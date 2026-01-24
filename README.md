## Automehaničarski servis – IPVO projekt

### Pokretanje
docker-compose up --build

### Arhitektura
NGINX → HAProxy → API → PostgreSQL

### Testiranje load balancinga
for i in {1..10}; do curl -s http://localhost:8080/health; echo; done

### Faze

~~1. faza: Implementacija osnovnih funkcionalnosti naručivanja servisa: korisnici mogu kreirati, pregledati i otkazati narudžbe, a mehaničari pregledavati i ažurirati statuse vozila. Sustav se sastoji od web poslužitelja i relacijske baze podataka (npr. PostgreSQL) uz leaderless pristup replikaciji radi veće otpornosti. Aplikacija je kontejnerizirana pomoću Dockera, a skalabilnost se osigurava load balancerom i replikacijom baze podataka.~~

2. faza: Omogućeno pretraživanje narudžbi prema datumu ili statusu. Za real-time obavijesti o promjenama statusa koristi se RabbitMQ kao message broker. Dodana je predmemorija (Memcached) za često korištene podatke (npr. popis aktivnih servisa koje mehaničari često otvaraju) radi poboljšanja performansi.

3. faza: Uvedeno asinkrono generiranje mjesečnih izvještaja o servisnim aktivnostima i korištenju dijelova koristeći job schedulere (npr. Apache Airflow). Implementirano monitoriranje performansi i opterećenja korištenjem Prometheusa za prikupljanje metrika i Grafane za vizualizaciju.

## <span style="color:purple">Nakon što otkriješ da si nekako instalirao docker 2 puta</text>

![Monkey](https://media.newyorker.com/photos/59095bb86552fa0be682d9d0/master/pass/Monkey-Selfie.jpg)
