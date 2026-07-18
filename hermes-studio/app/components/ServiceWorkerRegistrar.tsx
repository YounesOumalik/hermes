'use client';

import { useEffect } from 'react';

/**
 * Enregistre le Service Worker de l'app pour activer :
 *  - Cache offline (manifest pages + assets statiques)
 *  - Économie réseau pour les assets inchangés
 *
 * No-op en développement (le SW peut interférer avec HMR).
 */
export default function ServiceWorkerRegistrar() {
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (process.env.NODE_ENV !== 'production') return;
    if (!('serviceWorker' in navigator)) return;

    const register = async () => {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
          updateViaCache: 'none',
        });
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (!newWorker) return;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // Nouvelle version disponible, on attend un reload user
              console.info('[Hermes] Nouvelle version disponible. Rechargez pour mettre à jour.');
            }
          });
        });
        console.info('[Hermes] Service Worker enregistré:', registration.scope);
      } catch (err) {
        console.warn('[Hermes] Échec d\'enregistrement du Service Worker:', err);
      }
    };

    // Petit délai pour ne pas bloquer le rendu initial
    const timer = window.setTimeout(register, 1500);
    return () => window.clearTimeout(timer);
  }, []);

  return null;
}
