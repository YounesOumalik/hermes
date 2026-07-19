#!/bin/bash
# scripts/migrate.sh — Lance les migrations Alembic dans le container hermes-core
# Usage: ./scripts/migrate.sh [upgrade|downgrade|revision] [target]
#
# Exemples :
#   ./scripts/migrate.sh                  # upgrade head (défaut)
#   ./scripts/migrate.sh upgrade head
#   ./scripts/migrate.sh downgrade -1
#   ./scripts/migrate.sh revision -m "add foo"

set -euo pipefail

CMD="${1:-upgrade}"
TARGET="${2:-head}"

# Détecter le nom du container (alias possible : hermes-core OU compose-...-hermes-core-1)
CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '(^|/)hermes-core$' | head -1 || true)
if [ -z "$CONTAINER" ]; then
    # Fallback : docker-compose naming
    CONTAINER=$(docker ps --format '{{.Names}}' | grep 'hermes-core' | head -1)
fi

if [ -z "$CONTAINER" ]; then
    echo "❌ Container hermes-core introuvable. Lancer d'abord :"
    echo "   cd /opt/hermes-orchestration/repo && docker compose up -d hermes-core"
    exit 1
fi

echo "→ Cible : $CMD $TARGET"
echo "→ Container : $CONTAINER"

case "$CMD" in
    upgrade|downgrade)
        docker exec "$CONTAINER" alembic "$CMD" "$TARGET"
        ;;
    revision)
        shift 2
        docker exec "$CONTAINER" alembic revision --autogenerate "$@"
        ;;
    history)
        docker exec "$CONTAINER" alembic history
        ;;
    current)
        docker exec "$CONTAINER" alembic current
        ;;
    *)
        echo "Commandes supportées : upgrade | downgrade | revision | history | current"
        exit 1
        ;;
esac

echo "✅ OK"