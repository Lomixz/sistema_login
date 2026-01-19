"""
Análisis detallado de slots ocupados por Jesus Erick
"""
from app import app, db
from models import Grupo, AsignacionProfesorGrupo, DisponibilidadProfesor, Horario, HorarioAcademico, User

with app.app_context():
    # Buscar a Jesus Erick
    prof = User.query.filter(User.nombre.like('%Jesus%'), User.apellido.like('%Fernandez%')).first()
    
    if not prof:
        print('Profesor no encontrado')
        exit()
    
    print(f'Análisis de slots para: {prof.nombre} {prof.apellido}')
    print('='*60)
    
    dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
    horarios_mat = Horario.query.filter_by(turno='matutino', activo=True).order_by(Horario.orden).all()
    
    # Crear matriz de disponibilidad
    print('\n📅 Disponibilidad del profesor (matutino):')
    print('         | Lun | Mar | Mie | Jue | Vie |')
    print('-'*50)
    
    for h in horarios_mat:
        row = f'{h.hora_inicio.strftime("%H:%M")} |'
        for dia in dias:
            disp = DisponibilidadProfesor.query.filter_by(
                profesor_id=prof.id,
                horario_id=h.id,
                dia_semana=dia,
                activo=True,
                disponible=True
            ).first()
            
            if disp:
                row += '  ✓  |'
            else:
                row += '  -  |'
        print(row)
    
    # Mostrar horarios ocupados
    print('\n📋 Horarios ya asignados:')
    ocupados = HorarioAcademico.query.filter_by(
        profesor_id=prof.id,
        activo=True
    ).all()
    
    print('         | Lun | Mar | Mie | Jue | Vie |')
    print('-'*50)
    
    for h in horarios_mat:
        row = f'{h.hora_inicio.strftime("%H:%M")} |'
        for dia in dias:
            ha = HorarioAcademico.query.filter_by(
                profesor_id=prof.id,
                horario_id=h.id,
                dia_semana=dia,
                activo=True
            ).first()
            
            if ha:
                row += f' {ha.grupo[:3]}|'
            else:
                row += '     |'
        print(row)
    
    print('\nDetalle de horarios ocupados:')
    for ha in ocupados:
        print(f'  - {ha.grupo}: {ha.materia.codigo} - {ha.dia_semana} {ha.horario.hora_inicio.strftime("%H:%M")}')
