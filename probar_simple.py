"""
Prueba simplificada de generación de horarios
"""
from app import app, db
from models import (
    Grupo, Materia, AsignacionProfesorGrupo, DisponibilidadProfesor, 
    Horario, HorarioAcademico
)
from ortools.sat.python import cp_model

def probar_grupo_simple(grupo_codigo):
    with app.app_context():
        grupo = Grupo.query.filter_by(codigo=grupo_codigo, activo=True).first()
        if not grupo:
            print(f"Grupo {grupo_codigo} no encontrado")
            return
        
        print(f"Probando generación para grupo: {grupo.codigo}")
        print("="*60)
        
        # Datos básicos
        turno_str = "matutino" if grupo.turno == "M" else "vespertino"
        horarios = Horario.query.filter_by(turno=turno_str, activo=True).order_by(Horario.orden).all()
        dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        
        print(f"Horarios del turno {turno_str}: {len(horarios)}")
        print(f"Días: {len(dias)}")
        print(f"Total slots: {len(horarios) * len(dias)}")
        
        # Materias y profesores
        materias_info = []
        for m in grupo.materias:
            if not m.activa:
                continue
            asig = AsignacionProfesorGrupo.query.filter_by(
                grupo_id=grupo.id, materia_id=m.id, activo=True
            ).first()
            if asig and asig.profesor:
                materias_info.append({
                    'materia': m,
                    'profesor': asig.profesor,
                    'horas': m.horas_semanales or 3
                })
            else:
                print(f"  ❌ {m.codigo}: Sin profesor asignado")
        
        print(f"\nMaterias con profesor: {len(materias_info)}")
        total_horas = sum(mi['horas'] for mi in materias_info)
        print(f"Total horas requeridas: {total_horas}")
        
        # Crear modelo simplificado
        model = cp_model.CpModel()
        variables = {}
        
        # Crear variables
        for mi in materias_info:
            m = mi['materia']
            for h in horarios:
                for dia_idx, dia in enumerate(dias):
                    var_name = f"M{m.id}_H{h.id}_D{dia_idx}"
                    variables[(m.id, h.id, dia_idx)] = model.NewBoolVar(var_name)
        
        print(f"Variables creadas: {len(variables)}")
        
        # Restricción 1: Horas por materia
        for mi in materias_info:
            m = mi['materia']
            horas_req = mi['horas']
            vars_materia = []
            for h in horarios:
                for dia_idx in range(len(dias)):
                    key = (m.id, h.id, dia_idx)
                    if key in variables:
                        vars_materia.append(variables[key])
            
            if vars_materia:
                model.Add(sum(vars_materia) == horas_req)
                print(f"  {m.codigo}: {horas_req}h con {len(vars_materia)} variables")
        
        # Restricción 2: No conflicto de grupo (una materia por slot)
        for h in horarios:
            for dia_idx in range(len(dias)):
                vars_slot = []
                for mi in materias_info:
                    m = mi['materia']
                    key = (m.id, h.id, dia_idx)
                    if key in variables:
                        vars_slot.append(variables[key])
                
                if vars_slot:
                    model.Add(sum(vars_slot) <= 1)
        
        # Restricción 3: Disponibilidad de profesores
        restricciones_disp = 0
        for mi in materias_info:
            m = mi['materia']
            p = mi['profesor']
            
            for h in horarios:
                for dia_idx, dia in enumerate(dias):
                    disp = DisponibilidadProfesor.query.filter_by(
                        profesor_id=p.id,
                        horario_id=h.id,
                        dia_semana=dia,
                        activo=True,
                        disponible=True
                    ).first()
                    
                    if not disp:
                        key = (m.id, h.id, dia_idx)
                        if key in variables:
                            model.Add(variables[key] == 0)
                            restricciones_disp += 1
        
        print(f"Restricciones de disponibilidad: {restricciones_disp}")
        
        # Restricción 4: No conflicto de profesor
        profesor_materias = {}
        for mi in materias_info:
            p_id = mi['profesor'].id
            if p_id not in profesor_materias:
                profesor_materias[p_id] = []
            profesor_materias[p_id].append(mi['materia'])
        
        for p_id, mats in profesor_materias.items():
            if len(mats) > 1:
                print(f"  Profesor {p_id} tiene {len(mats)} materias")
                for h in horarios:
                    for dia_idx in range(len(dias)):
                        vars_prof = []
                        for m in mats:
                            key = (m.id, h.id, dia_idx)
                            if key in variables:
                                vars_prof.append(variables[key])
                        
                        if len(vars_prof) > 1:
                            model.Add(sum(vars_prof) <= 1)
        
        # Restricción 5: Horarios existentes
        restricciones_exist = 0
        for mi in materias_info:
            m = mi['materia']
            p = mi['profesor']
            
            ha_existentes = HorarioAcademico.query.filter(
                HorarioAcademico.profesor_id == p.id,
                HorarioAcademico.activo == True,
                HorarioAcademico.grupo != grupo.codigo
            ).all()
            
            for ha in ha_existentes:
                try:
                    dia_idx = dias.index(ha.dia_semana)
                except ValueError:
                    continue
                
                key = (m.id, ha.horario_id, dia_idx)
                if key in variables:
                    model.Add(variables[key] == 0)
                    restricciones_exist += 1
        
        print(f"Restricciones por horarios existentes: {restricciones_exist}")
        
        # Resolver
        print("\nResolviendo...")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60
        
        status = solver.Solve(model)
        
        print(f"\nEstado: {solver.StatusName(status)}")
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print("\n✅ SOLUCIÓN ENCONTRADA:")
            
            for mi in materias_info:
                m = mi['materia']
                horas_asignadas = 0
                print(f"\n{m.codigo} ({mi['horas']}h):")
                for h in horarios:
                    for dia_idx, dia in enumerate(dias):
                        key = (m.id, h.id, dia_idx)
                        if key in variables and solver.Value(variables[key]) == 1:
                            print(f"  - {dia} {h.hora_inicio.strftime('%H:%M')}")
                            horas_asignadas += 1
                print(f"  Total: {horas_asignadas}h")
        else:
            print("\n❌ NO SE ENCONTRÓ SOLUCIÓN")

if __name__ == "__main__":
    import sys
    grupo_codigo = sys.argv[1] if len(sys.argv) > 1 else "1MTII1"
    probar_grupo_simple(grupo_codigo)
