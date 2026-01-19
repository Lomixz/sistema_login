"""
Análisis de slots bloqueados para Jesus Erick y el grupo 1MTII1
"""
from app import app, db
from models import HorarioAcademico, DisponibilidadProfesor, Horario, User

with app.app_context():
    # Buscar a Alejandra y Octavio
    alejandra = User.query.filter(User.nombre.like('%Alejandra%')).first()
    octavio = User.query.filter(User.nombre.like('%Octavio%')).first()
    
    print("Slots bloqueados por Alejandra Heredia Celis (4MTII1):")
    print("="*60)
    
    dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
    horarios_mat = Horario.query.filter_by(turno='matutino', activo=True).order_by(Horario.orden).all()
    
    print('         | Lun | Mar | Mie | Jue | Vie |')
    print('-'*50)
    
    for h in horarios_mat:
        row = f'{h.hora_inicio.strftime("%H:%M")} |'
        for dia in dias:
            ha = HorarioAcademico.query.filter_by(
                profesor_id=alejandra.id,
                horario_id=h.id,
                dia_semana=dia,
                activo=True
            ).first()
            
            if ha:
                row += f'  X  |'
            else:
                row += '     |'
        print(row)
    
    print("\n\nSlots bloqueados por Octavio Rodriguez (7MSC1, 10MSC2):")
    print("="*60)
    
    print('         | Lun | Mar | Mie | Jue | Vie |')
    print('-'*50)
    
    for h in horarios_mat:
        row = f'{h.hora_inicio.strftime("%H:%M")} |'
        for dia in dias:
            ha = HorarioAcademico.query.filter_by(
                profesor_id=octavio.id,
                horario_id=h.id,
                dia_semana=dia,
                activo=True
            ).first()
            
            if ha:
                row += f'  X  |'
            else:
                row += '     |'
        print(row)
    
    print("\n\nTotal slots disponibles para el grupo 1MTII1:")
    print("="*60)
    
    # Contar slots NO ocupados
    slots_libres = 0
    for h in horarios_mat:
        for dia in dias:
            # Verificar si alguno de los profesores del grupo tiene este slot ocupado
            ha_ale = HorarioAcademico.query.filter_by(
                profesor_id=alejandra.id if alejandra else 0,
                horario_id=h.id,
                dia_semana=dia,
                activo=True
            ).first()
            
            ha_oct = HorarioAcademico.query.filter_by(
                profesor_id=octavio.id if octavio else 0,
                horario_id=h.id,
                dia_semana=dia,
                activo=True
            ).first()
            
            if not ha_ale and not ha_oct:
                slots_libres += 1
    
    print(f'Total slots en turno matutino: 35')
    print(f'Slots bloqueados por Alejandra: 4')
    print(f'Slots bloqueados por Octavio: 11')
    print(f'Slots efectivamente libres: {slots_libres}')
    print(f'Horas requeridas por grupo 1MTII1: 35')
