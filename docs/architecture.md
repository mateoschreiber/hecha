# Arquitectura

El navegador sólo accede a Caddy. Caddy reenvía `/api/*` a FastAPI y el resto a Next.js. Web y API leen exclusivamente datos locales; PostgreSQL es la fuente de verdad y Redis es prescindible. El worker es el único proceso que consulta SILpy y conserva payload crudo, errores recuperables y checkpoints transaccionales.
