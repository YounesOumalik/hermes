#!/usr/bin/env node
/**
 * build-icons.mjs — Régénère les icônes PNG à partir de public/icon.svg
 * Usage : node scripts/build-icons.mjs
 * Nécessite : ImageMagick (`convert` dans le PATH)
 */
import { execSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const PUBLIC = resolve(ROOT, 'public');

function checkConvert() {
  try {
    execSync('which convert', { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function build(src, dest, size, density) {
  const cmd = `convert -background none -density ${density} ${src} -resize ${size}x${size} ${dest}`;
  execSync(cmd, { stdio: 'inherit' });
  console.log(`✓ ${dest}`);
}

if (!checkConvert()) {
  console.error('❌ ImageMagick `convert` introuvable. Installez-le : sudo apt install imagemagick');
  process.exit(1);
}

if (!existsSync(resolve(PUBLIC, 'icon.svg'))) {
  console.error('❌ public/icon.svg manquant.');
  process.exit(1);
}

console.log('🎨 Génération des icônes PWA…');
build(`${PUBLIC}/icon.svg`, `${PUBLIC}/icons/icon-192.png`, 192, 384);
build(`${PUBLIC}/icon.svg`, `${PUBLIC}/icons/icon-512.png`, 512, 1024);
build(`${PUBLIC}/icon.svg`, `${PUBLIC}/apple-icon.png`, 180, 384);
build(`${PUBLIC}/icon.svg`, `${PUBLIC}/favicon.ico`, 32, 384);
build(
  `${PUBLIC}/icons/icon-maskable-512.svg`,
  `${PUBLIC}/icons/icon-maskable-512.png`,
  512,
  1024
);
console.log('✅ Toutes les icônes sont générées dans public/');
