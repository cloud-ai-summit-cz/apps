## Trip Service Security

- All endpoints require Bearer JWT from Entra ID
- Read operations: any authenticated principal
- Mutating operations (create/update/delete, gallery changes): only toy owner
- Toy ownership verified by calling Toy Service with forwarded bearer token
