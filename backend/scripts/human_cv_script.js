'use strict';
/**
 * NTS CV Analysis Script
 * Processes a video file using @vladmandic/human (TensorFlow.js) via ffmpeg.
 * Outputs one JSON line per frame to stdout; stderr is for diagnostics only.
 *
 * Usage: node human_cv_script.js <video_path> [sample_fps]
 * Env:   HUMAN_DIR  - path to human-main repo (default /human)
 *        NODE_PATH  - path containing node_modules with tfjs-node + pipe2jpeg
 */

const fs = require('fs');
const path = require('path');
const { spawn, spawnSync } = require('child_process');

const videoPath = process.argv[2];
const sampleFps = parseInt(process.argv[3], 10) || 2;

if (!videoPath) {
    process.stderr.write('Usage: node human_cv_script.js <video_path> [sample_fps]\n');
    process.exit(1);
}

if (!fs.existsSync(videoPath)) {
    process.stderr.write(`Video file not found: ${videoPath}\n`);
    process.exit(1);
}

const HUMAN_DIR = process.env.HUMAN_DIR || '/human';

// Load Human - it bundles its own tfjs-node internally
const Human = require(path.join(HUMAN_DIR, 'dist', 'human.node.js'));
const HumanClass = Human.Human || Human.default || Human;

// Load Pipe2Jpeg - installed at container level via NODE_PATH
const Pipe2Jpeg = require('pipe2jpeg');

const humanConfig = {
    modelBasePath: 'file://' + path.join(HUMAN_DIR, 'models') + '/',
    debug: false,
    async: true,
    filter: { enabled: false },
    face: {
        enabled: true,
        detector: { enabled: true, rotation: false, return: true, maxDetected: 10 },
        mesh: { enabled: true },
        iris: { enabled: true },
        emotion: { enabled: true },
        description: { enabled: false }, // age/gender – skip for speed
    },
    body: { enabled: true },
    hand: { enabled: true, maxDetected: 10 },
    object: { enabled: false },
};

const human = new HumanClass(humanConfig);

let videoInfo = { fps: 0, width: 0, height: 0, duration_ms: 0 };
let frameCount = 0;
let outputCount = 0;
// Frame queue — process all frames sequentially so the @vladmandic/human
// tracker never loses state. The old isBusy/drop approach caused the tracker
// to reset mid-video and re-assign face IDs from 0, swapping person labels.
const frameQueue = [];
let isProcessingQueue = false;

function log(msg) {
    process.stderr.write(`[cv] ${msg}\n`);
}

async function drainQueue() {
    if (isProcessingQueue) return;
    isProcessingQueue = true;
    while (frameQueue.length > 0) {
        const { jpegBuffer, frameIndex } = frameQueue.shift();
        await processFrame(jpegBuffer, frameIndex);
    }
    isProcessingQueue = false;
}

function getVideoMetadata(videoFile) {
    const result = spawnSync('ffprobe', [
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        videoFile,
    ], { encoding: 'utf-8' });

    if (result.status !== 0) {
        log('ffprobe failed: ' + (result.stderr || ''));
        return;
    }

    try {
        const data = JSON.parse(result.stdout);
        const stream = (data.streams || []).find(s => s.codec_type === 'video');
        if (stream) {
            const parts = (stream.r_frame_rate || '25/1').split('/');
            videoInfo.fps = parts.length === 2 ? parseFloat(parts[0]) / parseFloat(parts[1]) : parseFloat(parts[0]);
            videoInfo.width = stream.width || 0;
            videoInfo.height = stream.height || 0;
            const dur = parseFloat(stream.duration || stream.tags?.DURATION || '0');
            videoInfo.duration_ms = isFinite(dur) ? Math.round(dur * 1000) : 0;
            log(`Video: ${videoInfo.width}x${videoInfo.height} @ ${videoInfo.fps.toFixed(2)}fps, ${videoInfo.duration_ms}ms`);
        }
    } catch (e) {
        log('ffprobe parse error: ' + e.message);
    }
}

async function processFrame(jpegBuffer, frameIndex) {
    // No isBusy guard — frames are queued and drained sequentially.
    try {
        const tf = human.tf;
        const tensor = tf.node.decodeJpeg(jpegBuffer, 3);
        const result = await human.detect(tensor);
        tf.dispose(tensor);

        const timestamp_ms = Math.round((frameIndex / sampleFps) * 1000);

        const w = videoInfo.width || 1;
        const h = videoInfo.height || 1;

        const faces = (result.face || []).map((f, i) => {
            const rot = f.rotation;
            return {
                id: f.id !== undefined ? f.id : i,
                score: parseFloat((f.faceScore || f.score || f.boxScore || 0).toFixed(4)),
                box: f.box ? [f.box[0]/w, f.box[1]/h, f.box[2]/w, f.box[3]/h] : null,
                rotation: rot && rot.angle ? {
                    yaw: parseFloat(rot.angle.yaw.toFixed(4)),
                    pitch: parseFloat(rot.angle.pitch.toFixed(4)),
                    roll: parseFloat(rot.angle.roll.toFixed(4)),
                } : null,
                gaze: rot && rot.gaze ? {
                    bearing: parseFloat(rot.gaze.bearing.toFixed(4)),
                    strength: parseFloat(rot.gaze.strength.toFixed(4)),
                } : null,
                emotion: (f.emotion || []).map(e => ({
                    emotion: e.emotion,
                    score: parseFloat(e.score.toFixed(4)),
                })),
                mesh_count: f.mesh ? f.mesh.length : 0,
            };
        });

        const bodies = (result.body || []).map((b, i) => {
            return {
                id: b.id !== undefined ? b.id : i,
                score: parseFloat((b.score || 0).toFixed(4)),
                box: b.box ? [b.box[0]/w, b.box[1]/h, b.box[2]/w, b.box[3]/h] : null,
                keypoints: (b.keypoints || []).map(k => {
                    const kx = k.x !== undefined ? k.x : (k.position ? k.position[0] : 0);
                    const ky = k.y !== undefined ? k.y : (k.position ? k.position[1] : 0);
                    return {
                        name: k.name,
                        x: kx / w,
                        y: ky / h,
                        score: parseFloat((k.score || 0).toFixed(4))
                    };
                })
            };
        });

        const hands = (result.hand || []).map((h, i) => {
            return {
                id: h.id !== undefined ? h.id : i,
                score: parseFloat((h.score || 0).toFixed(4)),
                box: h.box ? [h.box[0]/w, h.box[1]/h, h.box[2]/w, h.box[3]/h] : null,
                label: h.label,
                keypoints: (h.keypoints || []).map(k => ({
                    x: k[0] / w,
                    y: k[1] / h,
                    z: (k[2] || 0)
                }))
            };
        });

        // Only write output if at least one person detected
        if (faces.length > 0 || bodies.length > 0 || hands.length > 0) {
            const line = JSON.stringify({
                frame: frameIndex,
                timestamp_ms,
                faces,
                bodies,
                hands,
            });
            process.stdout.write(line + '\n');
            outputCount++;
        }
    } catch (e) {
        log(`Frame ${frameIndex} error: ${e.message}`);
    }
}

async function main() {
    log(`Loading human models from ${HUMAN_DIR}/models/`);
    await human.load();
    await human.warmup();
    log('Human ready. Processing: ' + videoPath + ' @ ' + sampleFps + ' fps sample rate');

    getVideoMetadata(videoPath);

    const ffmpegArgs = [
        '-loglevel', 'error',
        '-i', videoPath,
        '-an',                         // drop audio
        '-vf', `fps=${sampleFps}`,     // sample at configured fps
        '-c:v', 'mjpeg',               // output MJPEG
        '-pix_fmt', 'yuvj420p',
        '-f', 'image2pipe',
        'pipe:1',
    ];

    const ffmpeg = spawn('ffmpeg', ffmpegArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
    const pipe2jpeg = new Pipe2Jpeg();

    ffmpeg.stderr.on('data', d => log('ffmpeg: ' + d.toString().trim()));
    ffmpeg.stdout.pipe(pipe2jpeg);

    // Queue every frame — no drops — so the human tracker stays continuous.
    pipe2jpeg.on('data', (jpeg) => {
        const currentFrame = ++frameCount;
        frameQueue.push({ jpegBuffer: jpeg, frameIndex: currentFrame });
        drainQueue().catch(e => log('queue drain error: ' + e.message));
    });

    await new Promise((resolve) => {
        ffmpeg.on('close', async (code) => {
            log(`ffmpeg done (code=${code}). Draining remaining ${frameQueue.length} queued frames...`);
            // Wait for the queue to fully drain
            while (frameQueue.length > 0 || isProcessingQueue) {
                await new Promise(r => setTimeout(r, 100));
            }
            resolve();
        });
    });

    // Write summary line
    process.stdout.write(JSON.stringify({
        __summary__: true,
        total_frames: frameCount,
        frames_with_detections: outputCount,
        video_fps: parseFloat(videoInfo.fps.toFixed(3)),
        width: videoInfo.width,
        height: videoInfo.height,
        duration_ms: videoInfo.duration_ms,
    }) + '\n');

    log(`Done. Processed ${frameCount} frames, ${outputCount} had detections.`);
    process.exit(0);
}

main().catch(e => {
    log('Fatal: ' + e.message + '\n' + e.stack);
    process.exit(1);
});
