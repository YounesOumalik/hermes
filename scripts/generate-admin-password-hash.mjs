#!/usr/bin/env node
import { randomBytes, scryptSync } from 'node:crypto';
import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

const username = process.argv[2] || 'admin';
const readline = createInterface({ input, output });
const password = await readline.question('Nouveau mot de passe (12 caractères minimum) : ');
readline.close();

if (password.length < 12) {
  console.error('Le mot de passe doit contenir au moins 12 caractères.');
  process.exit(1);
}

const salt = randomBytes(16);
const hash = scryptSync(password, salt, 64, { N: 16384, r: 8, p: 1 });
console.log(`HERMES_ADMIN_USERNAME=${username}`);
console.log(`HERMES_ADMIN_PASSWORD_HASH=scrypt$${salt.toString('base64url')}$${hash.toString('base64url')}`);
