# Data Flow & Pipeline Architecture

```
                  [ Distributed Locust Workers ]
                                |
               HTTP POST /api/v1/events/playback
                                |
                                v
                +-------------------------------+
                |   FastAPI Ingestion Endpoint  |
                +-------------------------------+
                                |
               Pydantic Schema Payload Validation
                                |
                                v
                +-------------------------------+
                |     Run Status Verification   |
                |   (Must be in 'running' state)|
                +-------------------------------+
                    /                       \
        [Inactive] /                         \ [Active]
                  v                           v
     +--------------------------+     +-------------------------------+
     | Increment Rejected Count |     | Execute Atomic Redis Lua      |
     | Raise 409 Conflict Error |     | Script (INGEST_EVENT_LUA)     |
     +--------------------------+     +-------------------------------+
                                                 |
                                       Atomic SISMEMBER Check
                                                 |
                                       +---------+---------+
                         [Duplicate ID]|                   |[New Event ID]
                                       v                   v
                        +----------------------+ +-----------------------------+
                        | HINCRBY duplicates   | | SADD processed_events       |
                        | HINCRBY submissions  | | HINCRBY accepted_events     |
                        | Return 202 Duplicate | | HINCRBY total_watch_duration|
                        +----------------------+ | HINCRBY event_types         |
                                                 | SADD viewers                |
                                                 | LPUSH recent_timestamps     |
                                                 | Return 202 Accepted         |
                                                 +-----------------------------+
                                                               |
                                                               v
                                                 +-----------------------------+
                                                 | When Run Stops or Batches:  |
                                                 | Flush Redis Stats to        |
                                                 | PostgreSQL EventSummary &   |
                                                 | SimulationMetric Records    |
                                                 +-----------------------------+
```
