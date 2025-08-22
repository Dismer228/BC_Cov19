## MongoDB supplementary data schema (for comments, annotations, and external sources)

### Objectives
- **Capture user-generated context**: comments on specific data points, threaded discussions, reactions.
- **Persist annotations**: quality flags, classifications, corrections with time validity.
- **Link additional sources**: URLs, files, APIs not present in Snowflake.
- **Anchor to Snowflake rows/columns** without duplicating facts stored in the warehouse.

---

### Collections overview
- **comments**: threaded user discussions anchored to a data target.
- **annotations**: structured labels/flags about a target, with validity windows.
- **sources**: metadata for external sources (URLs, files, APIs) not in Snowflake.
- **files** (optional): attachment metadata if storing binaries (recommend GridFS or external object storage).
- **audit_log** (optional): immutable change log for moderation/governance.

---

### Shared subdocument: `target`
Anchors a record to a specific warehouse location (typically Snowflake) and optionally to a row and/or column.

```json
{
  "warehouse": "snowflake",          
  "database": "PUBLIC_DB",           
  "schema": "COVID",                
  "table": "cases_by_region",       
  "row_pk_hash": "b3c8...f1a0",     
  "row_locator": {                    
    "region_id": "BC-01",
    "date": { "$date": "2025-01-02T00:00:00Z" }
  },
  "column": "cases",                 
  "metric": null,                     
  "data_value": 1234,                 
  "data_value_fetched_at": { "$date": "2025-08-22T15:30:00Z" }
}
```

Notes:
- Use either `row_pk_hash` (preferred, precomputed deterministic hash of the primary key(s)) or `row_locator` (map of PK column-value pairs). Both can coexist.
- `column` is optional; omit to anchor the entire row.
- `data_value` is a snapshot for context and is not a source of truth; warehouse remains authoritative.

---

### Collection: `comments`
Free-form, threaded comments tied to a target, with moderation and simple reactions.

Create with schema validation:
```js
// comments
db.createCollection("comments", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["target", "body", "created_by", "created_at", "status"],
      properties: {
        _id: { bsonType: "objectId" },
        project_id: { bsonType: ["objectId", "string" ] },
        target: {
          bsonType: "object",
          required: ["warehouse", "database", "schema", "table"],
          properties: {
            warehouse: { enum: ["snowflake", "external", "other"] },
            database: { bsonType: "string", minLength: 1 },
            schema: { bsonType: "string", minLength: 1 },
            table: { bsonType: "string", minLength: 1 },
            row_pk_hash: { bsonType: "string", pattern: "^[a-f0-9]{64}$" },
            row_locator: {
              bsonType: "object",
              additionalProperties: {
                bsonType: ["string", "int", "long", "double", "decimal", "date", "objectId", "bool"]
              }
            },
            column: { bsonType: "string" },
            metric: { bsonType: ["string", "null"] },
            data_value: { bsonType: ["string", "int", "long", "double", "decimal", "bool", "null"] },
            data_value_fetched_at: { bsonType: ["date", "null"] }
          },
          oneOf: [
            { required: ["row_pk_hash"] },
            { required: ["row_locator"] },
            { } // allow table-level comments without row selector
          ]
        },
        body: { bsonType: "string", minLength: 1, description: "Markdown/plaintext" },
        parent_comment_id: { bsonType: ["objectId", "null"] },
        thread_id: { bsonType: ["objectId", "null"] },
        mentions: { bsonType: "array", items: { bsonType: "string" }, uniqueItems: true },
        tags: { bsonType: "array", items: { bsonType: "string" }, uniqueItems: true },
        reactions: {
          bsonType: "object",
          additionalProperties: { bsonType: "int" } // e.g. {"thumbs_up": 3}
        },
        attachments: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["storage"],
            properties: {
              storage: { enum: ["gridfs", "s3", "gcs", "url"] },
              file_id: { bsonType: "objectId" },
              url: { bsonType: "string" },
              filename: { bsonType: "string" },
              media_type: { bsonType: "string" },
              size_bytes: { bsonType: "int" },
              sha256: { bsonType: "string", pattern: "^[a-f0-9]{64}$" }
            }
          }
        },
        status: { enum: ["open", "resolved", "archived"] },
        visibility: { enum: ["public", "internal", "private"], description: "Access scope" },
        acl: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["subject_type", "subject_id", "permission"],
            properties: {
              subject_type: { enum: ["user", "team", "role"] },
              subject_id: { bsonType: "string" },
              permission: { enum: ["read", "comment", "admin"] }
            }
          }
        },
        created_by: {
          bsonType: "object",
          required: ["id", "name"],
          properties: {
            id: { bsonType: "string" },
            name: { bsonType: "string" },
            email: { bsonType: ["string", "null"] }
          }
        },
        updated_by: {
          bsonType: ["object", "null"],
          properties: {
            id: { bsonType: "string" },
            name: { bsonType: "string" },
            email: { bsonType: ["string", "null"] }
          }
        },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: ["date", "null"] },
        archived_at: { bsonType: ["date", "null"] },
        is_deleted: { bsonType: "bool" },
        deleted_at: { bsonType: ["date", "null"] },
        deleted_by: { bsonType: ["string", "null"] }
      }
    }
  }
});

// Indexes for common access patterns
db.comments.createIndexes([
  { key: { "target.database": 1, "target.schema": 1, "target.table": 1, "target.row_pk_hash": 1, "target.column": 1, status: 1 }, name: "by_target_row_col_status" },
  { key: { "target.database": 1, "target.schema": 1, "target.table": 1, "target.row_locator.region_id": 1, "target.row_locator.date": 1 }, name: "by_locator_example" },
  { key: { thread_id: 1, created_at: 1 }, name: "by_thread_time" },
  { key: { parent_comment_id: 1 }, name: "by_parent" },
  { key: { "created_by.id": 1, created_at: -1 }, name: "by_author_time" },
  { key: { tags: 1 }, name: "by_tags" },
  { key: { body: "text" }, name: "text_body" },
  { key: { archived_at: 1 }, name: "ttl_archived", expireAfterSeconds: 0 } // expires when archived_at is set
]);
```

---

### Collection: `annotations`
Structured, queryable facts about a target, with validity windows and versioning.

```js
// annotations
db.createCollection("annotations", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["target", "type", "created_by", "created_at", "status"],
      properties: {
        _id: { bsonType: "objectId" },
        project_id: { bsonType: ["objectId", "string"] },
        target: {
          bsonType: "object",
          required: ["warehouse", "database", "schema", "table"],
          properties: {
            warehouse: { enum: ["snowflake", "external", "other"] },
            database: { bsonType: "string" },
            schema: { bsonType: "string" },
            table: { bsonType: "string" },
            row_pk_hash: { bsonType: "string", pattern: "^[a-f0-9]{64}$" },
            row_locator: {
              bsonType: "object",
              additionalProperties: {
                bsonType: ["string", "int", "long", "double", "decimal", "date", "objectId", "bool"]
              }
            },
            column: { bsonType: "string" }
          }
        },
        type: { enum: ["note", "classification", "quality_issue", "correction", "flag"] },
        key: { bsonType: ["string", "null"], description: "Domain key, e.g., 'dq:outlier'" },
        properties: { bsonType: "object" },
        confidence: { bsonType: ["double", "int"], minimum: 0, maximum: 1 },
        status: { enum: ["active", "resolved", "superseded"] },
        valid_from: { bsonType: ["date", "null"] },
        valid_to: { bsonType: ["date", "null"] },
        is_latest: { bsonType: "bool" },
        supersedes: { bsonType: ["objectId", "null"] },
        superseded_by: { bsonType: ["objectId", "null"] },
        created_by: {
          bsonType: "object",
          required: ["id", "name"],
          properties: {
            id: { bsonType: "string" },
            name: { bsonType: "string" },
            email: { bsonType: ["string", "null"] }
          }
        },
        updated_by: { bsonType: ["object", "null"] },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: ["date", "null"] }
      }
    }
  }
});

// Indexes
db.annotations.createIndexes([
  { key: { "target.database": 1, "target.schema": 1, "target.table": 1, "target.row_pk_hash": 1, "target.column": 1 }, name: "by_target_row_col" },
  { key: { type: 1, status: 1 }, name: "by_type_status" },
  { key: { is_latest: 1 }, name: "by_latest" },
  { key: { valid_from: 1, valid_to: 1 }, name: "by_validity" },
  { key: { key: 1 }, name: "by_key" }
]);
```

---

### Collection: `sources`
External sources referenced by comments/annotations or used as supplementary context.

```js
// sources
db.createCollection("sources", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["title", "source_type", "added_by", "created_at"],
      properties: {
        _id: { bsonType: "objectId" },
        project_id: { bsonType: ["objectId", "string"] },
        title: { bsonType: "string", minLength: 1 },
        description: { bsonType: ["string", "null"] },
        source_type: { enum: ["url", "file", "api", "dataset", "other"] },
        url: { bsonType: ["string", "null"] },
        url_sha256: { bsonType: ["string", "null"], pattern: "^[a-f0-9]{64}$" },
        file_id: { bsonType: ["objectId", "null"] },
        api_spec: { bsonType: ["object", "null"] },
        publisher: { bsonType: ["string", "null"] },
        license: { bsonType: ["string", "null"] },
        language: { bsonType: ["string", "null"] },
        coverage: {
          bsonType: "object",
          properties: {
            time_from: { bsonType: ["date", "null"] },
            time_to: { bsonType: ["date", "null"] },
            geography: { bsonType: "array", items: { bsonType: "string" } }
          }
        },
        trust_score: { bsonType: ["int", "double", "null"], minimum: 0, maximum: 100 },
        tags: { bsonType: "array", items: { bsonType: "string" }, uniqueItems: true },
        linked_targets: { bsonType: "array", items: { bsonType: "object" } },
        added_by: {
          bsonType: "object",
          required: ["id", "name"],
          properties: {
            id: { bsonType: "string" },
            name: { bsonType: "string" },
            email: { bsonType: ["string", "null"] }
          }
        },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: ["date", "null"] }
      }
    }
  }
});

// Indexes
db.sources.createIndexes([
  { key: { url_sha256: 1 }, name: "uniq_url", unique: true, sparse: true },
  { key: { title: "text", description: "text", tags: 1 }, name: "text_title_desc_tags" },
  { key: { "coverage.time_from": 1, "coverage.time_to": 1 }, name: "by_time_coverage" }
]);
```

---

### Attachments: `files`
- Prefer storing binaries in object storage (S3/GCS) and keep only metadata and a signed URL in MongoDB.
- If you must store binaries in MongoDB, use GridFS. Store attachment metadata inside `comments.attachments` and/or a lightweight `files_meta` collection for cross-reference.

```js
// Optional files metadata
db.createCollection("files_meta", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["filename", "storage", "created_at"],
      properties: {
        _id: { bsonType: "objectId" },
        storage: { enum: ["gridfs", "s3", "gcs", "url"] },
        file_id: { bsonType: ["objectId", "null"] }, // GridFS id
        url: { bsonType: ["string", "null"] },
        filename: { bsonType: "string" },
        media_type: { bsonType: ["string", "null"] },
        size_bytes: { bsonType: ["int", "long", "null"] },
        sha256: { bsonType: ["string", "null"], pattern: "^[a-f0-9]{64}$" },
        created_at: { bsonType: "date" },
        created_by: { bsonType: "string" }
      }
    }
  }
});
```

---

### Example documents

Comment on a specific row+column in Snowflake:
```json
{
  "_id": { "$oid": "66c70a2f9b5f1d4a4d6930a1" },
  "project_id": "bc_covid19",
  "target": {
    "warehouse": "snowflake",
    "database": "PUBLIC_DB",
    "schema": "COVID",
    "table": "cases_by_region",
    "row_locator": { "region_id": "BC-01", "date": { "$date": "2025-01-02T00:00:00Z" } },
    "column": "cases",
    "data_value": 1234,
    "data_value_fetched_at": { "$date": "2025-08-22T15:30:00Z" }
  },
  "body": "Spike due to data backlog clearance.",
  "status": "open",
  "tags": ["backfill", "alert"],
  "mentions": ["user:analyst.alice"],
  "attachments": [
    { "storage": "url", "url": "https://example.org/ops-note", "filename": "ops-note" }
  ],
  "created_by": { "id": "user:analyst.alice", "name": "Alice" },
  "created_at": { "$date": "2025-08-22T15:35:00Z" }
}
```

Annotation marking an outlier for a row:
```json
{
  "_id": { "$oid": "66c70a2f9b5f1d4a4d6930b2" },
  "target": {
    "warehouse": "snowflake",
    "database": "PUBLIC_DB",
    "schema": "COVID",
    "table": "cases_by_region",
    "row_pk_hash": "0d2c3a...91ef"
  },
  "type": "quality_issue",
  "key": "dq:outlier",
  "properties": { "method": "zscore", "z": 4.8 },
  "confidence": 0.92,
  "status": "active",
  "is_latest": true,
  "created_by": { "id": "user:qa.bob", "name": "Bob" },
  "created_at": { "$date": "2025-08-22T15:40:00Z" }
}
```

External source record:
```json
{
  "_id": { "$oid": "66c70a2f9b5f1d4a4d6930c3" },
  "title": "Provincial health update 2025-01-03",
  "source_type": "url",
  "url": "https://gov.bc.ca/health/updates/2025-01-03",
  "url_sha256": "f0b5e0...3a99",
  "coverage": { "time_from": { "$date": "2025-01-02T00:00:00Z" }, "time_to": { "$date": "2025-01-03T00:00:00Z" }, "geography": ["BC"] },
  "tags": ["press-release"],
  "added_by": { "id": "user:analyst.alice", "name": "Alice" },
  "created_at": { "$date": "2025-08-22T15:45:00Z" }
}
```

---

### Example queries

- Fetch open comments for a specific Snowflake row/column:
```js
db.comments.find({
  "target.database": "PUBLIC_DB",
  "target.schema": "COVID",
  "target.table": "cases_by_region",
  "target.row_locator.region_id": "BC-01",
  "target.row_locator.date": ISODate("2025-01-02T00:00:00Z"),
  "target.column": "cases",
  status: "open"
}).sort({ created_at: -1 })
```

- Fetch latest active quality annotations for a table:
```js
db.annotations.find({
  "target.database": "PUBLIC_DB",
  "target.schema": "COVID",
  "target.table": "cases_by_region",
  type: { $in: ["quality_issue", "correction"] },
  status: "active",
  is_latest: true
})
```

- Find sources that cover a given date range and geography:
```js
db.sources.find({
  "coverage.time_from": { $lte: ISODate("2025-01-02T00:00:00Z") },
  "coverage.time_to": { $gte: ISODate("2025-01-02T00:00:00Z") },
  "coverage.geography": "BC"
})
```

---

### Implementation notes
- Prefer deterministic `row_pk_hash` for stable targeting; fall back to `row_locator` when hashing is not available.
- Keep comments immutable except for status/edits; use `audit_log` for moderation if needed.
- Use `archived_at` TTL index to auto-expire archived comments; non-archived docs remain unaffected.
- For attachments, store binaries outside MongoDB when possible; keep hashes for integrity and deduplication.
- Consider adding `tenant_id`/`project_id` if multi-tenant separation is needed.