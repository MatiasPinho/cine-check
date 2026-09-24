# Monitor de Avengers Endgame: Bonus en IMAX Norcenter

Consulta cada hora las funciones publicadas para **IMAX Theatre (Norcenter)** en [la página de Showcase](https://entradas.todoshowcase.com/showcase/pelicula?filmid=6017&house_id=3250). Muestra todas las fechas y horarios disponibles y destaca las funciones que aparecieron desde la última ejecución.

La página carga los horarios con JavaScript desde una API JSON. El script consulta esa misma API directamente, sin depender del HTML renderizado, selectores CSS ni identificadores de funciones. Compara fecha, hora y formato. Conserva la fecha tal como la publica Showcase; un horario con `N` indica trasnoche.

## Publicar y activar

1. Subí **todo este directorio** como repositorio de GitHub, con el archivo `.github/workflows/monitor.yml` en la rama principal.
2. En la pestaña **Actions**, abrí **Monitorear IMAX Norcenter** y ejecutá **Run workflow** una vez para guardar el estado inicial. Esa primera ejecución registra las funciones existentes como punto de partida.
3. Luego GitHub Actions lo ejecuta cada hora, al minuto 17 UTC. En los logs del paso **Revisar funciones**, las incorporaciones aparecen como `¡NUEVAS FUNCIONES DETECTADAS!` y `NUEVA FUNCIÓN: fecha hora — formato`.

El archivo `state/showings.json` se crea en la primera ejecución y se actualiza mediante un commit del bot solo cuando cambia la lista. Se necesita que GitHub Actions pueda escribir en la rama principal; si esa rama tiene reglas de protección que impiden commits del bot, hay que permitirlos para que persista el estado. No se requieren secretos ni instalar paquetes de Python.

GitHub puede retrasar alguna ejecución programada. El workflow también permite iniciarlo manualmente desde **Actions**.

## Ejecutar localmente

Con Python 3.10 o posterior:

```bash
python monitor.py
```

La primera ejecución crea `state/showings.json`. Para probar sin alterar ese archivo:

```bash
python monitor.py --state /tmp/showcase-showings.json
```

Si la API falla o cambia de estructura, el script termina con error y conserva el estado anterior. El próximo intento vuelve a comparar contra el último estado válido.
