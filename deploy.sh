#!/usr/bin/env bash
# deploy do incept na vps (hostinger)
# rodar no servidor, como root:  bash /var/www/incept/deploy.sh
# use --help para ver as opcoes

set -euo pipefail

APP_DIR="/var/www/incept"
APP_USER="www-data"
SERVICE="gunicorn"
BRANCH="${BRANCH:-main}"
VENV="$APP_DIR/venv"
HEALTH_HOST="76.13.169.63"           # precisa estar no server_name do nginx e no ALLOWED_HOSTS
HEALTH_PATHS=("/" "/login/")

usage() {
    cat <<EOF
uso: bash $APP_DIR/deploy.sh [--deps]

passos:
  1. confere se nenhum arquivo foi alterado ou zerado direto no servidor (se tiver, cancela)
  2. baixa a branch $BRANCH do github (so fast-forward, nunca sobrescreve nada)
  3. roda pip install se o requirements.txt mudou
  4. roda o manage.py check (se falhar, para antes de mexer no site)
  5. aplica as migrations
  6. roda o collectstatic
  7. reinicia o $SERVICE e confere se o site responde 200

opcoes:
  --deps     roda o pip install mesmo se o requirements.txt nao mudou
  -h,--help  mostra esta ajuda

variaveis:
  BRANCH     branch do deploy (padrao: main). ex: BRANCH=develop bash deploy.sh
EOF
}

FORCE_DEPS=0
for arg in "$@"; do
    case "$arg" in
        --deps) FORCE_DEPS=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "opcao desconhecida: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

step() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERRO: %s\n' "$*" >&2; exit 1; }
as_app() { sudo -u "$APP_USER" "$@"; }
manage() { as_app "$VENV/bin/python" manage.py "$@"; }

OLD_REV=""
rollback_hint() {
    if [ -n "$OLD_REV" ] && [ "$OLD_REV" != "$(git rev-parse HEAD)" ]; then
        echo "para voltar o codigo para a versao anterior: cd $APP_DIR && git reset --hard $OLD_REV && bash deploy.sh" >&2
    fi
}

[ "$(id -u)" -eq 0 ] || fail "rode como root (o script usa sudo -u $APP_USER e reinicia o $SERVICE)"
cd "$APP_DIR"

# 1. estado do servidor ---------------------------------------------------------
step "conferindo o estado do servidor"
current_branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$current_branch" = "$BRANCH" ] || fail "o servidor esta na branch '$current_branch', mas o deploy e da '$BRANCH'"

changed="$(git status --porcelain --untracked-files=no)"
if [ -n "$changed" ]; then
    echo "$changed"
    fail "tem arquivos alterados direto no servidor (lista acima). deploy cancelado para nao perder nada.
  - arquivo zerado ou apagado por engano: git checkout -- <arquivo>
  - mudanca de verdade: leve ela para o repositorio, faca commit e push, depois rode: git checkout -- <arquivo>"
fi

# 2. codigo novo ------------------------------------------------------------------
step "baixando a branch $BRANCH do github"
OLD_REV="$(git rev-parse HEAD)"
git fetch --quiet origin "$BRANCH"
NEW_REV="$(git rev-parse "origin/$BRANCH")"

if [ "$OLD_REV" = "$NEW_REV" ]; then
    echo "ja esta na versao mais recente: $(git log -1 --format='%h %s')"
else
    git log --oneline "$OLD_REV..$NEW_REV"
    git merge --ff-only --quiet "origin/$BRANCH" \
        || fail "nao deu para atualizar com fast-forward (o servidor tem commits que nao estao no github)"
fi

# git rodou como root: devolve os arquivos para o usuario do gunicorn
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 3. dependencias -----------------------------------------------------------------
if [ "$FORCE_DEPS" -eq 1 ] || ! git diff --quiet "$OLD_REV" HEAD -- requirements.txt; then
    step "instalando dependencias (requirements.txt)"
    as_app "$VENV/bin/pip" install --no-cache-dir --quiet -r requirements.txt \
        || { rollback_hint; fail "o pip install falhou. o site NAO foi reiniciado"; }
else
    step "requirements.txt nao mudou, pulando o pip install (use --deps para forcar)"
fi

# 4. checagem ---------------------------------------------------------------------
step "conferindo o projeto (manage.py check)"
manage check || { rollback_hint; fail "o django encontrou problemas. o site NAO foi reiniciado"; }

# 5. migrations -------------------------------------------------------------------
step "aplicando migrations"
manage migrate --noinput || { rollback_hint; fail "as migrations falharam. o site NAO foi reiniciado"; }

# 6. arquivos estaticos -----------------------------------------------------------
step "coletando arquivos estaticos (collectstatic)"
manage collectstatic --noinput || { rollback_hint; fail "o collectstatic falhou. o site NAO foi reiniciado"; }

# 7. reinicia e confere -----------------------------------------------------------
step "reiniciando o $SERVICE"
systemctl restart "$SERVICE"
sleep 2
if ! systemctl is-active --quiet "$SERVICE"; then
    journalctl -u "$SERVICE" -n 30 --no-pager
    rollback_hint
    fail "o $SERVICE nao subiu (log acima)"
fi

step "conferindo se o site responde"
for path in "${HEALTH_PATHS[@]}"; do
    code="000"
    for _ in 1 2 3 4 5; do
        code="$(curl -s -o /dev/null -w '%{http_code}' -m 10 -H "Host: $HEALTH_HOST" "http://127.0.0.1$path" || true)"
        [ "$code" = "200" ] && break
        sleep 2
    done
    echo "$path -> $code"
    if [ "$code" != "200" ]; then
        journalctl -u "$SERVICE" -n 40 --no-pager
        rollback_hint
        fail "$path respondeu $code em vez de 200"
    fi
done

step "deploy concluido: $(git log -1 --format='%h %s')"
