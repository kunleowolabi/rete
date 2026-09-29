# Architecture notes

Two things in this codebase aren't self-explanatory from the code alone.
Everything else, read the Terraform or the source directly.

## Why the RDS Data API instead of a normal database connection

The API and loader Lambdas talk to Aurora through the **RDS Data API**
(`execute_statement`), not a persistent driver connection. This is why a
Lambda can reach the database with no VPC and no NAT gateway — otherwise
required for outbound internet access from inside a VPC, and a fixed
monthly cost regardless of traffic.

It also explains three things you'll see in every handler:

- **Retry-with-backoff on every query** (`execute_with_retry()` in
  `data_api_utils.py`). Aurora scales to zero when idle, and the first
  call after it wakes up fails with `DatabaseResumingException` until
  it's ready. This is handled, not a bug.
- **Typed field unwrapping** (`unwrap_records()`). The Data API returns
  every value wrapped in a type tag; this is the one place that gets
  flattened.
- **Pre-simplified geometry** on `/boundaries/*` and `/lines`. The Data
  API caps a response at 1MB, so these run
  `ST_SimplifyPreserveTopology()` server-side rather than returning full
  resolution.

## The MapLibre worker fix

MapLibre GL's worker script isn't bundled correctly by Vite's production
build — it resolves its own worker path at runtime in a way that assumes
a live `node_modules`, which doesn't exist in a static deploy. The fix:
copy the worker and its internal dependency into `public/maplibre/` as
untouched static files, and point MapLibre at that fixed path directly:

```javascript
import * as maplibregl from "maplibre-gl";
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
```

If you upgrade `maplibre-gl`, re-copy both files from
`node_modules/maplibre-gl/dist/` — they're not managed by the build.