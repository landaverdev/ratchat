/*
 * Dirección del servidor de IA y chat (el que corre en Render.com).
 * La web vive en ratchatapp.com y se conecta a este servidor por WebSocket.
 * Si tu servicio de Render tiene otra dirección, cámbiala aquí.
 * Para probar todo en tu computadora, déjala vacía ("") y ejecuta: SERVIR_WEB=1 uvicorn app:app
 */
window.RATCHAT_CONFIG = {
  servidor: "https://ratchat.onrender.com",
};
