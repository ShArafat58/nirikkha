-- Nirikkha schema v1: filings + chunks with pgvector and full-text search.
-- Idempotent: safe to run more than once.

create extension if not exists vector;

create table if not exists filings (
    accession_no      text primary key,
    cik               text not null,
    company           text not null,
    form              text not null,
    filing_date       date not null,
    report_date       date,
    url               text not null,
    page_count        int,
    has_page_markers  boolean not null default false,
    created_at        timestamptz not null default now()
);

create table if not exists chunks (
    chunk_id          text primary key,
    accession_no      text not null references filings (accession_no) on delete cascade,
    section_key       text not null,
    section_title     text not null,
    page_start        int,
    page_end          int,
    paragraph_start   int not null,
    paragraph_end     int not null,
    context_header    text not null,
    text              text not null,
    char_count        int not null,
    content_hash      text not null,
    embedding         vector(384),
    tsv               tsvector generated always as (to_tsvector('english', context_header || ' ' || text)) stored
);

create index if not exists filings_cik_idx on filings (cik);
create index if not exists chunks_accession_idx on chunks (accession_no);
create index if not exists chunks_embedding_hnsw on chunks using hnsw (embedding vector_cosine_ops);
create index if not exists chunks_tsv_gin on chunks using gin (tsv);

-- The database is only reached by our backend (Data API disabled). RLS on, no public policies.
alter table filings enable row level security;
alter table chunks enable row level security;