-- Restore knowledge-vault Storage RLS compatibility for both historical
-- Vault uploads ({user_id}/...) and generated media uploads
-- (media/{user_id}/...). Migration 0049 narrowed the policy to media-only,
-- which blocks browser signed URL creation for existing user Vault files.

DO $$
BEGIN
    IF to_regclass('storage.objects') IS NULL THEN
        RAISE NOTICE 'Supabase storage.objects is unavailable. Skipping knowledge-vault storage RLS update.';
    ELSE
        DROP POLICY IF EXISTS "Users can access their own files in knowledge-vault" ON storage.objects;

        CREATE POLICY "Users can access their own files in knowledge-vault" ON storage.objects
            FOR ALL
            TO authenticated
            USING (
                bucket_id = 'knowledge-vault'
                AND (
                    split_part(name, '/', 1) = auth.uid()::text
                    OR (
                        split_part(name, '/', 1) = 'media'
                        AND split_part(name, '/', 2) = auth.uid()::text
                    )
                )
            )
            WITH CHECK (
                bucket_id = 'knowledge-vault'
                AND (
                    split_part(name, '/', 1) = auth.uid()::text
                    OR (
                        split_part(name, '/', 1) = 'media'
                        AND split_part(name, '/', 2) = auth.uid()::text
                    )
                )
            );
    END IF;
END $$;
