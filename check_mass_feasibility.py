from app import app, db
from models import Grupo, AsignacionProfesorGrupo, DisponibilidadProfesor

def check_mass_feasibility():
    with app.app_context():
        grupos = Grupo.query.filter_by(activo=True).all()
        print(f"Analizando factibilidad para {len(grupos)} grupos activos...")
        
        # 1. Mapa de Profesor -> Horas Requeridas Totales
        profesor_horas = {} # {profesor_id: {'nombre': str, 'horas_total': int, 'grupos': [], 'asignaciones': []}}
        
        for grupo in grupos:
            print(f"\nGrupo {grupo.codigo}:")
            # Obtener asignaciones
            # Fallback: si no hay asignaciones explicitas, usar materia.profesores (pero eso es ambiguo)
            # Usaremos la lógica del generador: AsignacionProfesorGrupo o default
            
            materias_procesadas = set()
            
            # 1. Asignaciones explícitas
            asigs = AsignacionProfesorGrupo.query.filter_by(grupo_id=grupo.id, activo=True).all()
            for asig in asigs:
                if asig.materia_id in materias_procesadas: continue
                materias_procesadas.add(asig.materia_id)
                
                p = asig.profesor
                if not p: continue
                
                if p.id not in profesor_horas:
                    profesor_horas[p.id] = {'nombre': f"{p.nombre} {p.apellido}", 'horas_total': 0, 'grupos': set(), 'temas': []}
                
                horas = asig.horas_semanales
                profesor_horas[p.id]['horas_total'] += horas
                profesor_horas[p.id]['grupos'].add(grupo.codigo)
                profesor_horas[p.id]['temas'].append(f"{grupo.codigo}:{horas}h")
                
            # 2. Materias sin asignación explícita (simulación simple)
            for materia in grupo.materias:
                if materia.id in materias_procesadas: continue
                # Aquí es difícil saber quién la dará, pero asumiremos que NO cuenta por ahora o cuenta al "primer" profesor disponible
                # Para masivo, asumimos que si no hay asignación, el sistema trata de asignar a alguien. 
                # Pero el error actual es "Infeasible", probablemente por los que SI están asignados.
                pass

        print("\n--- ANÁLISIS DE RECURSOS COMPARTIDOS ---")
        conflictos = False
        for pid, data in profesor_horas.items():
            # Obtener disponibilidad real
            disp_slots = DisponibilidadProfesor.query.filter_by(profesor_id=pid, activo=True, disponible=True).count()
            
            req = data['horas_total']
            grupos_str = ", ".join(data['grupos'])
            
            print(f"Profesor: {data['nombre']}")
            print(f"  - Requiere: {req} horas (para grupos: {grupos_str})")
            print(f"  - Disponibles: {disp_slots} slots")
            
            if req > disp_slots:
                print(f"  ❌ CONFLICTO CRÍTICO: Necesita {req} horas pero solo tiene {disp_slots} disponibles.")
                conflictos = True
            elif req > 40: # Límite legal o físico razonable
                 print(f"  ⚠️ ALERTA: Carga excesiva ({req} horas).")
                 conflictos = True
            else:
                 print("  ✅ OK")

        if conflictos:
            print("\nCONCLUSIÓN: La generación masiva falla porque los profesores compartidos no tienen suficientes horas para atender a TODOS los grupos simultáneamente.")
        else:
            print("\nCONCLUSIÓN: No se detectaron conflictos obvios de horas totales. El problema podría ser de distribución (ej. todos quieren Lunes 7am).")

if __name__ == '__main__':
    check_mass_feasibility()
