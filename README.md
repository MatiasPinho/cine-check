# Monitor de Avengers Endgame: Bonus en IMAX Norcenter

Consulta cada hora las funciones publicadas para **IMAX Theatre (Norcenter)** en [la página de Showcase](https://entradas.todoshowcase.com/showcase/pelicula?filmid=6017&house_id=3250). Muestra todas las fechas y horarios disponibles y envía una notificación de GitHub cuando aparece una función nueva.

La página carga los horarios con JavaScript desde una API JSON. El script consulta esa misma API directamente, sin depender del HTML renderizado, selectores CSS ni identificadores de funciones. Compara fecha, hora y formato. Conserva la fecha tal como la publica Showcase; un horario con `N` indica trasnoche.

## Publicar y activar

1. Subí **todo este directorio** como repositorio de GitHub, con el archivo `.github/workflows/monitor.yml` en la rama principal.
2. En la pestaña **Actions**, abrí **Monitorear IMAX Norcenter** y ejecutá **Run workflow** una vez para guardar el estado inicial. Esa primera ejecución registra las funciones existentes como punto de partida.
3. Luego GitHub Actions lo ejecuta cada hora, al minuto 17 UTC. El resumen de cada ejecución muestra los horarios; en los logs del paso **Revisar funciones**, las incorporaciones aparecen como `¡NUEVAS FUNCIONES DETECTADAS!` y `NUEVA FUNCIÓN: fecha hora — formato`.

Si aparece una fecha, un horario o un formato que nunca se había visto, el workflow crea un issue con una tabla de las nuevas funciones y el enlace a Showcase, y lo asigna al dueño del repositorio. Esto genera una notificación de GitHub según las [preferencias de notificación de la cuenta](https://github.com/settings/notifications). La primera ejecución, las ejecuciones sin cambios y las que solo eliminan funciones no crean issues. Un horario reprogramado se considera nuevo si su fecha u hora difiere del estado anterior; si una función antigua desaparece y vuelve, no se repite el aviso.

El archivo `state/showings.json` se crea en la primera ejecución y se actualiza mediante un commit del bot solo cuando cambia la lista. Se necesita que GitHub Actions pueda escribir en la rama principal y crear issues; si esa rama tiene reglas de protección que impiden commits del bot, hay que permitirlos para que persista el estado. No se requieren secretos ni instalar paquetes de Python.

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
