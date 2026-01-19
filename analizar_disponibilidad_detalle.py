"""
Análisis detallado de disponibilidad por profesor
"""
from app import app, db
from models import (
    Grupo, AsignacionProfesorGrupo, DisponibilidadProfesor, 
    Horario
)

with app.app_context():
    grupo = Grupo.query.filter_by(codigo='1MTII1').first()
    
    turno_str = "matutino"
    horarios = Horario.query.filter_by(turno=turno_str, activo=True).order_by(Horario.orden).all()
    dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
    
    print("Análisis de disponibilidad por profesor para grupo 1MTII1")
    print("="*70)
    print(f"Turno: {turno_str}")
    print(f"Horarios: {len(horarios)} ({[h.hora_inicio.strftime('%H:%M') for h in horarios]})")
    print(f"Días: {dias}")
    print(f"Total slots posibles: {len(horarios) * len(dias)}")
    print()
    
    for m in grupo.materias:
        if not m.activa:
            continue
        
        asig = AsignacionProfesorGrupo.query.filter_by(
            grupo_id=grupo.id, materia_id=m.id, activo=True
        ).first()
        
        if not asig or not asig.profesor:
            continue
        
        p = asig.profesor
        print(f"\n{m.codigo} - {p.nombre} {p.apellido}")
        print("-"*50)
        
        # Contar disponibilidad
        slots_disponibles = 0
        slots_no_disponibles = 0
        
        print('         | Lun | Mar | Mie | Jue | Vie |')
        print('-'*50)
        
        for h in horarios:
            row = f'{h.hora_inicio.strftime("%H:%M")} |'
            for dia in dias:
                disp = DisponibilidadProfesor.query.filter_by(
                    profesor_id=p.id,
                    horario_id=h.id,
                    dia_semana=dia,
                    activo=True,
                    disponible=True
                ).first()
                
                if disp:
                    row += '  ✓  |'
                    slots_disponibles += 1
                else:
                    row += '  -  |'
                    slots_no_disponibles += 1
            print(row)
        
        print(f"\nDisponibles: {slots_disponibles}, No disponibles: {slots_no_disponibles}")
        print(f"Horas requeridas: {m.horas_semanales}")
        
        if slots_disponibles < (m.horas_semanales or 3):
            print("⚠️ PROBLEMA: No hay suficientes slots disponibles!")
