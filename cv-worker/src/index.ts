import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import os from 'os';
import * as tf from '@tensorflow/tfjs-node';
import { Human, Config } from '@vladmandic/human';
import ffmpegPath from 'ffmpeg-static';

const args = process.argv.slice(2);
if (args.length < 2) {
    console.error('Usage: npx ts-node src/index.ts <input_video_path> <output_json_path>');
    process.exit(1);
}

const inputVideo = path.resolve(args[0]);
const outputJson = path.resolve(args[1]);

const fps = 1;

async function extractFrames(videoPath: string, outputDir: string): Promise<string[]> {
    return new Promise((resolve, reject) => {
        if (!ffmpegPath) {
            reject(new Error("ffmpeg binary not found"));
            return;
        }

        const args = [
            '-i', videoPath,
            '-vf', `fps=${fps}`,
            path.join(outputDir, 'frame-%04d.jpg')
        ];

        const ffmpeg = spawn(ffmpegPath, args);

        ffmpeg.on('close', (code) => {
            if (code === 0) {
                const files = fs.readdirSync(outputDir)
                                .filter(f => f.startsWith('frame-') && f.endsWith('.jpg'))
                                .sort()
                                .map(f => path.join(outputDir, f));
                resolve(files);
            } else {
                reject(new Error(`ffmpeg exited with code ${code}`));
            }
        });
    });
}

async function main() {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cv-worker-'));
    try {
        console.log(`Extracting frames from ${inputVideo}...`);
        const frameFiles = await extractFrames(inputVideo, tmpDir);
        console.log(`Extracted ${frameFiles.length} frames.`);

        const config: Partial<Config> = {
            backend: 'tensorflow',
            body: { enabled: true },
            face: { enabled: true, emotion: { enabled: true } },
            gaze: { enabled: true },
            hand: { enabled: false },
            gesture: { enabled: false },
            segmentation: { enabled: false },
        };

        const human = new Human(config);
        console.log('Warming up human...');
        await human.warmup();

        const outputData = [];

        for (let i = 0; i < frameFiles.length; i++) {
            const framePath = frameFiles[i];
            const buffer = fs.readFileSync(framePath);
            const tensor = tf.node.decodeImage(buffer, 3);
            
            const result = await human.detect(tensor as any);
            
            // cleanup tensor
            tf.dispose(tensor);

            // process result, remove embeddings
            const cleanResult = {
                face: result.face.map((f: any) => {
                    const { embedding, ...rest } = f;
                    return rest;
                }),
                body: result.body,
                gaze: result.face.map((f: any) => f.gaze).filter(Boolean)
            };

            outputData.push({
                frame_index: i,
                timestamp_ms: i * (1000 / fps),
                results: cleanResult
            });
            console.log(`Processed frame ${i + 1}/${frameFiles.length}`);
        }

        fs.writeFileSync(outputJson, JSON.stringify(outputData, null, 2));
        console.log(`Results saved to ${outputJson}`);

    } catch (err) {
        console.error(err);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
}

main();
