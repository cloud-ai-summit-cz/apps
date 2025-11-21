## Demo Data Init Security

- All calls require Bearer JWT
- Caller must hold the configured admin role (default `Admin.FullAccess`)
- Service forwards caller token to Toy and Trip APIs
