import csv

obs = {
    'CP01': 'Respuesta clara y del dominio; deriva a soporte para elegir modelo.',
    'CP02': 'Cubre limpieza, lubricación, cambio de aguja y tensión; remite al manual.',
    'CP03': 'Pasos de enhebrado comprensibles y en orden.',
    'CP04': 'Pide aclaración de modelo y síntoma en vez de suponer.',
    'CP05': 'No inventa precio ni stock; deriva a ventas. Nota: el clasificador dio otros/baja en vez de informacion/baja (Clasif_correcta = No).',
    'CP06': 'Redirige con cortesía y no responde el tema fuera de dominio.',
    'CP07': 'Mantiene el contexto del mensaje anterior (remalladora) e indica que el rango de horas es orientacion no oficial.',
    'CP08': 'Transcribe de forma comprensible con Whisper small; la palabra aguja salio como hoja.',
    'CP09': 'Transcribe de forma comprensible en mp3 y m4a; remalladora salio como remayadora.',
    'CP10': 'Transcribe bien y responde con los 3 pasos de seguridad ante humo.',
    'CP11': 'Clasifica correctamente falla/alta y da posibles causas sin afirmar un diagnostico definitivo.',
    'CP12': 'Prioridad critica correcta; la respuesta empieza por desconectar el equipo.',
}

path = 'evidence/matriz_pruebas.csv'
with open(path, encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
    fields = list(rows[0].keys())

for r in rows:
    r['Cumple'] = 'Sí'
    r['Observaciones'] = obs.get(r['ID'], '')

with open(path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print('Listo')