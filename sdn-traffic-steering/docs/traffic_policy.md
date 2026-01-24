## Traffic Classification Policy

| Host | Traffic Type | Priority | Example |
|----|----|----|----|
| h1 | Control / VoIP | High | ICMP, UDP |
| h2 | Enterprise | Medium | TCP |
| h3 | Server | N/A | Responds |
| h4 | Best-effort | Low | Bulk traffic |

## Steering Logic
- High priority traffic → shortest / least hops
- Best-effort traffic → alternate path
