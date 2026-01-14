## Automehaničarski servis – IPVO projekt

### Pokretanje
docker-compose up --build

### Arhitektura
NGINX → HAProxy → API → PostgreSQL

### Testiranje load balancinga
for i in {1..10}; do curl -s http://localhost:8080/health; echo; done

![Monkey](https://media.newyorker.com/photos/59095bb86552fa0be682d9d0/master/pass/Monkey-Selfie.jpg)
