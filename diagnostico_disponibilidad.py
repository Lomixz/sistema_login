"""
Script para diagnosticar por qué el generador no encuentra disponibilidad vespertina
"""
from app import app
from models import db, Horario, User, DisponibilidadProfesor, AsignacionProfesorGrupo, Grupo

DIAS_SEMANA = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']

with app.app_context():
    # Probar con Andrea Lee Rangel (ID:7) que supuestamente no tiene disponibilidad vespertina
    prof_id = 7  # Andrea Lee Rangel
    prof = User.query.get(prof_id)
    print(f'Analizando: {prof.nombre} {prof.apellido} (ID: {prof_id})')
    print()
    
    # 1. Horarios vespertinos
    print('=== HORARIOS VESPERTINO ===')
    horarios_vesp = Horario.query.filter_by(turno='vespertino', activo=True).all()
    for h in horarios_vesp:
        print(f'  ID:{h.id} - {h.hora_inicio.strftime("%H:%M")} - {h.turno}')
    
    print()
    print('=== DISPONIBILIDAD VESPERTINA DE ANDREA ===')
    
    # Contar disponibilidad como lo hace el generador
    slots_totales = 0
    for horario_id in [h.id for h in horarios_vesp]:
        for dia in DIAS_SEMANA:
            disp = DisponibilidadProfesor.query.filter_by(
                profesor_id=prof_id,
                horario_id=horario_id,
                dia_semana=dia,
                activo=True,
                disponible=True,
            ).first()
            if disp:
                slots_totales += 1
                
    print(f'  Slots disponibles (método generador): {slots_totales}')
    
    # Ahora verificar TODOS sus registros de disponibilidad
    print()
    print('=== TODOS LOS REGISTROS DE DISPONIBILIDAD DE ANDREA ===')
    todas_disp = DisponibilidadProfesor.query.filter_by(profesor_id=prof_id).all()
    print(f'  Total registros: {len(todas_disp)}')
    
    # Agrupar por horario
    por_horario = {}
    for d in todas_disp:
        if d.horario_id not in por_horario:
            por_horario[d.horario_id] = []
        por_horario[d.horario_id].append(d)
    
    for h_id, disps in sorted(por_horario.items()):
        horario = Horario.query.get(h_id)
        turno = horario.turno if horario else "???"
        disponibles = sum(1 for d in disps if d.disponible and d.activo)
        print(f'  Horario ID:{h_id} ({turno}): {disponibles}/{len(disps)} disponibles')
    
    print()
    print('=== VERIFICAR QUE LOS DIAS COINCIDEN ===')
    # Ver qué días tiene registrados para un horario vespertino
    h_vesp_id = horarios_vesp[0].id if horarios_vesp else None
    if h_vesp_id:
        disps_h = DisponibilidadProfesor.query.filter_by(profesor_id=prof_id, horario_id=h_vesp_id).all()
        print(f'  Horario ID:{h_vesp_id}:')
        for d in disps_h:
            print(f'    dia_semana="{d.dia_semana}", disponible={d.disponible}, activo={d.activo}')
