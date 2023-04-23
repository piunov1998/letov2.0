# LETOV vol.2 | Discord Music Bot

Бот для проигрывания музыки в голосовых каналах discord

> old version: https://github.com/drews54/Discord-Music-Bot

## Installation and configuration

### docker-compose

```yaml
version: "3"

services:
  bot:
    image: letov

  postgres:
    image: postgres
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
```

### config
```yaml
pg:
  host: postgres
  port: 5432
  user: postgres
  password: postgres
  database: database

discord:
  token: YOUR_TOKEN
  prefix: @
```