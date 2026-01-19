"""
Script de diagnóstico rápido para ver el estado actual de los horarios
"""
from app import app, db
from models import Grupo, Materia, AsignacionProfesorGrupo, DisponibilidadProfesor, Horario, HorarioAcademico

with app.app_context():
    # Verificar grupos por turno
    grupos_mat = Grupo.query.filter_by(activo=True, turno='M').all()
    grupos_vesp = Grupo.query.filter_by(activo=True, turno='V').all()
    
    print("="*80)
    print(f'Grupos Matutinos: {len(grupos_mat)}')
    print("="*80)
    for g in grupos_mat:
        materias = [m for m in g.materias if m.activa]
        total_horas = sum(m.horas_semanales or 3 for m in materias)
        ha_count = HorarioAcademico.query.filter_by(grupo=g.codigo, activo=True).count()
        status = "✓" if ha_count >= total_horas else "❌"
        print(f'  {status} {g.codigo}: {len(materias)} materias, {total_horas}h requeridas, {ha_count} horarios generados')
    
    print()
    print("="*80)
    print(f'Grupos Vespertinos: {len(grupos_vesp)}')
    print("="*80)
    for g in grupos_vesp:
        materias = [m for m in g.materias if m.activa]
        total_horas = sum(m.horas_semanales or 3 for m in materias)
        ha_count = HorarioAcademico.query.filter_by(grupo=g.codigo, activo=True).count()
        status = "✓" if ha_count >= total_horas else "❌"
        print(f'  {status} {g.codigo}: {len(materias)} materias, {total_horas}h requeridas, {ha_count} horarios generados')
    
    # Verificar horarios (slots) disponibles por turno
    print()
    print("="*80)
    print('HORARIOS BASE')
    print("="*80)
    for turno in ['matutino', 'vespertino']:
        h = Horario.query.filter_by(turno=turno, activo=True).count()
        print(f'{turno}: {h} bloques horarios')
    
    # Verificar un grupo específico (1MTII1 que tiene 0 horarios)
    print()
    print("="*80)
    print("ANÁLISIS DETALLADO - Grupo 1MTII1")
    print("="*80)
    
    g = Grupo.query.filter_by(codigo='1MTII1').first()
    if g:
        print(f"Grupo: {g.codigo}")
        print(f"Turno: {g.turno} ({g.get_turno_display()})")
        
        materias = [m for m in g.materias if m.activa]
        print(f"\nMaterias ({len(materias)}):")
        for m in materias:
            # Buscar asignación específica
            asig = AsignacionProfesorGrupo.query.filter_by(
                grupo_id=g.id, materia_id=m.id, activo=True
            ).first()
            
            if asig and asig.profesor:
                # Verificar disponibilidad del profesor
                disp_count = DisponibilidadProfesor.query.filter_by(
                    profesor_id=asig.profesor_id,
                    activo=True,
                    disponible=True
                ).count()
                
                # Verificar si hay disponibilidad en turno matutino
                horarios_mat = Horario.query.filter_by(turno='matutino', activo=True).all()
                disp_matutino = 0
                for h in horarios_mat:
                    for dia in ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']:
                        d = DisponibilidadProfesor.query.filter_by(
                            profesor_id=asig.profesor_id,
                            horario_id=h.id,
                            dia_semana=dia,
                            activo=True,
                            disponible=True
                        ).first()
                        if d:
                            disp_matutino += 1
                
                print(f"  - {m.nombre} ({m.codigo}): {m.horas_semanales}h/semana")
                print(f"    Profesor: {asig.profesor.nombre} {asig.profesor.apellido}")
                print(f"    Disponibilidad total: {disp_count} slots")
                print(f"    Disponibilidad matutino: {disp_matutino} slots")
            else:
                print(f"  - {m.nombre} ({m.codigo}): {m.horas_semanales}h/semana")
                print(f"    ❌ SIN PROFESOR ASIGNADO")
        
        # Verificar horarios generados para este grupo
        print(f"\nHorarios generados:")
        ha_list = HorarioAcademico.query.filter_by(grupo=g.codigo, activo=True).all()
        if ha_list:
            for ha in ha_list[:10]:  # Solo mostrar primeros 10
                print(f"  - {ha.dia_semana}: {ha.materia.nombre} con {ha.profesor.nombre}")
        else:
            print("  ❌ No hay horarios generados para este grupo")
