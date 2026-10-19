-- Switch retrieval embeddings to the local bge-small-en-v1.5 model (384 dims).
-- Runs the change only if the column is not already vector(384), so re-running keeps data.
do $$
begin
    if (select format_type(atttypid, atttypmod)
          from pg_attribute
         where attrelid = 'public.chunks'::regclass and attname = 'embedding') <> 'vector(384)' then
        drop index if exists chunks_embedding_hnsw;
        update chunks set embedding = null;
        alter table chunks alter column embedding type vector(384);
    end if;
end $$;

create index if not exists chunks_embedding_hnsw on chunks using hnsw (embedding vector_cosine_ops);