#!/bin/bash
# Run after docker compose is up to apply the annotated video column migration.
# Usage: bash run_migration.sh
docker exec pjt-postgres-1 psql -U postgres -d nts_db -c "ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS annotated_video_key TEXT;"
echo "Migration complete: annotated_video_key column added to media_assets."
