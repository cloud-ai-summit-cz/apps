## Demo Data Init Service Architecture

The Demo Data Init Service is an admin-only orchestration API that reseeds
toys and trips by calling the Toy and Trip services.

### Responsibilities

- Trigger end-to-end demo data import
- Call Toy and Trip APIs using the caller's bearer token
- Return aggregate statistics about the import run
