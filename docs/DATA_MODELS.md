# Data Models

## 1. Principal Models

### 1.1 Base Principal
Represents an authenticated caller.
| Field | Type | Description |
|-------|------|-------------|
| subject_id | string | Unique identifier (oid for user, appid for system) |
| is_system | bool | True if workload/managed identity |
| roles | list[string] | App roles assigned (e.g., `System.Service`) |
| scopes | list[string] | OAuth scopes (e.g., `App.Access`) |
| issued_at | datetime | Token iat |
| expires_at | datetime | Token exp |

### 1.2 UserPrincipal (extends Base)
| Field | Type | Description |
| oid | string | Entra object id |
| display_name | string | Preferred username or name claim |

### 1.3 SystemPrincipal (extends Base)
| Field | Type | Description |
| app_id | string | Application ID / azp / appid |

### 1.4 AuthContext
| Field | Type | Description |
| principal | Principal | Resolved principal instance |
| raw_claims | dict | Original token claims for audit/troubleshooting |
| token_id | string | Derived from `jti` if present else hash of token header+claims |

## 2. Domain Model Adjustments

### 2.1 Toy
Add `owner_oid: string` (immutable except ownership transfer feature – future). Used to authorize create trip, order add-on, live geo actions.

### 2.2 Add-On Order
Implicitly links to trip and toy; authorization uses trip → toy → owner_oid chain.

## 3. Serialization / Storage
Principal models are not persisted; only `owner_oid` stored with toys. Token claims not stored server-side (stateless validation) except transient logging (structured fields).

## 4. Open Questions
* Need for soft-delete or transfer of toy ownership later? (Impacts `owner_oid` mutability.)
* Additional privacy attributes if global read model evolves.
