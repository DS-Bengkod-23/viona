#!/bin/bash
set -e

cd /app

if [ ! -d "vendor" ]; then
    echo "Installing Composer dependencies..."
    composer install --no-interaction
fi

if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

if ! grep -q "^APP_KEY=base64:" .env 2>/dev/null; then
    echo "Generating application key..."
    php artisan key:generate --force
fi

if grep -q "^DB_CONNECTION=sqlite" .env && [ ! -f "database/database.sqlite" ]; then
    echo "Creating SQLite database..."
    touch database/database.sqlite
fi

echo "Running database migrations..."
php artisan migrate --force

if [ ! -d "node_modules" ]; then
    echo "Installing NPM dependencies..."
    npm install
fi

if [ ! -d "public/build" ]; then
    echo "Building Vite assets..."
    npm run build
fi

echo "Starting Laravel server..."
exec php artisan serve --host=0.0.0.0 --port=8002
