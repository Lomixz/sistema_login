"""
Script de diagnóstico profundo para identificar por qué falla la generación masiva de horarios.
Analiza:
1. Distribución de disponibilidad por turno y día
2. Conflictos de horarios específicos (muchos profesores en mismo horario)
3. Materias sin profesor asignado
4. Desequilibrio entre turnos
"""

from app import app, db
from models import (Grupo, AsignacionProfesorGrupo, DisponibilidadProfesor, 
                    Materia, Horario, User)
from collections import defaultdict

def diagnostico_completo():
    with app.app_context():
        print("="*80)
        print("🔍 DIAGNÓSTICO PROFUNDO DE GENERACIÓN MASIVA DE HORARIOS")
        print("="*80)
        
        grupos = Grupo.query.filter_by(activo=True).all()
        
        if not grupos:
            print("❌ No hay grupos activos")
            return
        
        print(f"\n📊 Total de grupos activos: {len(grupos)}")
        
        # ============================================================
        # 1. ANÁLISIS POR GRUPO
        # ============================================================
        print("\n" + "="*80)
        print("📂 1. ANÁLISIS POR GRUPO")
        print("="*80)
        
        grupos_con_problemas = []
        total_horas_matutino = 0
        total_horas_vespertino = 0
        
        for grupo in grupos:
            print(f"\n--- Grupo: {grupo.codigo} ---")
            print(f"    Carrera: {grupo.get_carrera_nombre()}")
            print(f"    Cuatrimestre: {grupo.cuatrimestre}")
            print(f"    Turno: {grupo.get_turno_display()} ({grupo.turno})")
            
            # Materias del grupo
            materias = [m for m in grupo.materias if m.activa]
            print(f"    Materias activas: {len(materias)}")
            
            if not materias:
                print(f"    ❌ ERROR: Grupo sin materias asignadas")
                grupos_con_problemas.append((grupo.codigo, "Sin materias"))
                continue
            
            # Asignaciones profesor-materia-grupo
            asignaciones = AsignacionProfesorGrupo.query.filter_by(
                grupo_id=grupo.id, activo=True
            ).all()
            
            horas_grupo = 0
            materias_sin_profesor = []
            materias_con_profesor = []
            
            # Verificar asignaciones explícitas
            materias_con_asignacion = set()
            for asig in asignaciones:
                if asig.profesor:
                    materias_con_asignacion.add(asig.materia_id)
                    horas_grupo += asig.horas_semanales
                    materias_con_profesor.append(
                        f"      ✓ {asig.materia.nombre}: {asig.profesor.nombre} {asig.profesor.apellido} ({asig.horas_semanales}h)"
                    )
            
            # Verificar materias sin asignación explícita
            for materia in materias:
                if materia.id not in materias_con_asignacion:
                    # Verificar si tiene profesores en relación many-to-many
                    profesores_m2m = [p for p in materia.profesores if p.activo]
                    if profesores_m2m:
                        horas_materia = materia.horas_semanales or 3
                        horas_grupo += horas_materia
                        materias_con_profesor.append(
                            f"      ~ {materia.nombre}: {len(profesores_m2m)} profesores posibles (M2M, {horas_materia}h)"
                        )
                    else:
                        materias_sin_profesor.append(materia.nombre)
            
            print(f"    Horas totales requeridas: {horas_grupo}")
            
            if grupo.turno == 'M':
                total_horas_matutino += horas_grupo
            else:
                total_horas_vespertino += horas_grupo
            
            if materias_con_profesor:
                print("    Materias con profesor:")
                for m in materias_con_profesor[:5]:  # Mostrar solo primeras 5
                    print(m)
                if len(materias_con_profesor) > 5:
                    print(f"      ... y {len(materias_con_profesor) - 5} más")
            
            if materias_sin_profesor:
                print(f"    ❌ Materias SIN profesor asignado ({len(materias_sin_profesor)}):")
                for m in materias_sin_profesor:
                    print(f"      - {m}")
                grupos_con_problemas.append((grupo.codigo, f"{len(materias_sin_profesor)} materias sin profesor"))
        
        # ============================================================
        # 2. ANÁLISIS DE DISPONIBILIDAD POR TURNO
        # ============================================================
        print("\n" + "="*80)
        print("⏰ 2. ANÁLISIS DE DISPONIBILIDAD POR TURNO")
        print("="*80)
        
        horarios_matutino = Horario.query.filter_by(turno='matutino', activo=True).order_by(Horario.orden).all()
        horarios_vespertino = Horario.query.filter_by(turno='vespertino', activo=True).order_by(Horario.orden).all()
        
        print(f"\n    Horarios matutino: {len(horarios_matutino)}")
        for h in horarios_matutino:
            print(f"      {h.nombre}: {h.get_hora_inicio_str()} - {h.get_hora_fin_str()}")
        
        print(f"\n    Horarios vespertino: {len(horarios_vespertino)}")
        for h in horarios_vespertino:
            print(f"      {h.nombre}: {h.get_hora_inicio_str()} - {h.get_hora_fin_str()}")
        
        dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        
        # Capacidad por turno
        capacidad_matutino = len(horarios_matutino) * len(dias)
        capacidad_vespertino = len(horarios_vespertino) * len(dias)
        
        print(f"\n    📊 Capacidad semanal por turno (bloques horarios × días):")
        print(f"       Matutino: {capacidad_matutino} bloques ({len(horarios_matutino)} × {len(dias)})")
        print(f"       Vespertino: {capacidad_vespertino} bloques ({len(horarios_vespertino)} × {len(dias)})")
        
        print(f"\n    📊 Horas requeridas por turno:")
        print(f"       Matutino: {total_horas_matutino} horas")
        print(f"       Vespertino: {total_horas_vespertino} horas")
        
        # ============================================================
        # 3. ANÁLISIS DE DISPONIBILIDAD DE PROFESORES
        # ============================================================
        print("\n" + "="*80)
        print("👨‍🏫 3. ANÁLISIS DE DISPONIBILIDAD DE PROFESORES")
        print("="*80)
        
        # Recolectar todos los profesores que participan en los grupos
        profesores_involucrados = set()
        for grupo in grupos:
            asigs = AsignacionProfesorGrupo.query.filter_by(grupo_id=grupo.id, activo=True).all()
            for asig in asigs:
                if asig.profesor:
                    profesores_involucrados.add(asig.profesor)
            # También de relación M2M
            for materia in grupo.materias:
                for p in materia.profesores:
                    if p.activo:
                        profesores_involucrados.add(p)
        
        print(f"\n    Total profesores involucrados: {len(profesores_involucrados)}")
        
        # Analizar disponibilidad por turno
        disp_matutino = defaultdict(int)  # dia -> total_slots_disponibles
        disp_vespertino = defaultdict(int)
        
        for profesor in profesores_involucrados:
            disponibilidades = DisponibilidadProfesor.query.filter_by(
                profesor_id=profesor.id, activo=True, disponible=True
            ).all()
            
            for disp in disponibilidades:
                horario = Horario.query.get(disp.horario_id)
                if horario:
                    if horario.turno == 'matutino':
                        disp_matutino[disp.dia_semana] += 1
                    else:
                        disp_vespertino[disp.dia_semana] += 1
        
        print("\n    Slots de disponibilidad por día (todos los profesores):")
        print("    TURNO MATUTINO:")
        for dia in dias:
            count = disp_matutino[dia]
            print(f"      {dia.capitalize()}: {count} slots")
        total_disp_matutino = sum(disp_matutino.values())
        print(f"      TOTAL: {total_disp_matutino} slots")
        
        print("\n    TURNO VESPERTINO:")
        for dia in dias:
            count = disp_vespertino[dia]
            print(f"      {dia.capitalize()}: {count} slots")
        total_disp_vespertino = sum(disp_vespertino.values())
        print(f"      TOTAL: {total_disp_vespertino} slots")
        
        # ============================================================
        # 4. ANÁLISIS DE CONFLICTOS DE HORARIOS ESPECÍFICOS
        # ============================================================
        print("\n" + "="*80)
        print("⚠️  4. ANÁLISIS DE CONFLICTOS")
        print("="*80)
        
        # Para cada slot de tiempo, contar cuántos profesores pueden y cuántos grupos lo necesitan
        slots_problematicos = []
        
        for turno, horarios_turno in [('matutino', horarios_matutino), ('vespertino', horarios_vespertino)]:
            grupos_turno = [g for g in grupos if (g.turno == 'M' and turno == 'matutino') or 
                                                  (g.turno == 'V' and turno == 'vespertino')]
            
            for dia in dias:
                for horario in horarios_turno:
                    # Contar profesores disponibles en este slot
                    profesores_disponibles = DisponibilidadProfesor.query.filter_by(
                        horario_id=horario.id,
                        dia_semana=dia,
                        activo=True,
                        disponible=True
                    ).count()
                    
                    # Un grupo necesita exactamente 1 clase por slot (si tiene materias)
                    # Aquí grupos_turno todos necesitan cubrir ese slot potencialmente
                    grupos_necesitan = len(grupos_turno)
                    
                    if grupos_necesitan > profesores_disponibles:
                        slots_problematicos.append({
                            'turno': turno,
                            'dia': dia,
                            'horario': horario.nombre,
                            'hora': f"{horario.get_hora_inicio_str()}-{horario.get_hora_fin_str()}",
                            'grupos': grupos_necesitan,
                            'profesores_disponibles': profesores_disponibles,
                            'deficit': grupos_necesitan - profesores_disponibles
                        })
        
        if slots_problematicos:
            print("\n    ❌ SLOTS CON DÉFICIT DE PROFESORES:")
            # Ordenar por déficit
            slots_problematicos.sort(key=lambda x: x['deficit'], reverse=True)
            for slot in slots_problematicos[:15]:  # Top 15
                print(f"      {slot['turno'].upper()} {slot['dia'].capitalize()} {slot['hora']}:")
                print(f"        Grupos que necesitan: {slot['grupos']}")
                print(f"        Profesores disponibles: {slot['profesores_disponibles']}")
                print(f"        DÉFICIT: {slot['deficit']} profesores")
            if len(slots_problematicos) > 15:
                print(f"      ... y {len(slots_problematicos) - 15} slots más con problemas")
        else:
            print("\n    ✅ No se detectaron slots con déficit de profesores")
        
        # ============================================================
        # 5. RESUMEN Y RECOMENDACIONES
        # ============================================================
        print("\n" + "="*80)
        print("📋 5. RESUMEN Y RECOMENDACIONES")
        print("="*80)
        
        problemas_detectados = []
        recomendaciones = []
        
        # Problema 1: Grupos sin materias
        grupos_sin_materias = [g for g, msg in grupos_con_problemas if "Sin materias" in msg]
        if grupos_sin_materias:
            problemas_detectados.append(f"❌ {len(grupos_sin_materias)} grupo(s) sin materias")
            recomendaciones.append("👉 Asignar materias a todos los grupos")
        
        # Problema 2: Materias sin profesor
        grupos_materias_sin_prof = [g for g, msg in grupos_con_problemas if "materias sin profesor" in msg]
        if grupos_materias_sin_prof:
            problemas_detectados.append(f"❌ {len(grupos_materias_sin_prof)} grupo(s) con materias sin profesor")
            recomendaciones.append("👉 Asignar profesores a todas las materias de cada grupo")
        
        # Problema 3: Déficit de capacidad matutino
        if total_horas_matutino > total_disp_matutino:
            problemas_detectados.append(
                f"❌ Turno MATUTINO: Se requieren {total_horas_matutino} horas pero solo hay "
                f"{total_disp_matutino} slots de disponibilidad"
            )
            recomendaciones.append("👉 Aumentar disponibilidad de profesores en turno matutino")
            recomendaciones.append("👉 O reducir grupos/horas del turno matutino")
        
        # Problema 4: Déficit de capacidad vespertino
        if total_horas_vespertino > total_disp_vespertino:
            problemas_detectados.append(
                f"❌ Turno VESPERTINO: Se requieren {total_horas_vespertino} horas pero solo hay "
                f"{total_disp_vespertino} slots de disponibilidad"
            )
            recomendaciones.append("👉 Aumentar disponibilidad de profesores en turno vespertino")
        
        # Problema 5: Slots problemáticos
        if slots_problematicos:
            problemas_detectados.append(f"❌ {len(slots_problematicos)} slots con déficit de profesores")
            recomendaciones.append("👉 Verificar que los profesores tengan disponibilidad distribuida")
            recomendaciones.append("👉 Considerar agregar más profesores")
        
        print("\n🔴 PROBLEMAS DETECTADOS:")
        if problemas_detectados:
            for p in problemas_detectados:
                print(f"    {p}")
        else:
            print("    ✅ No se detectaron problemas mayores")
        
        print("\n🔵 RECOMENDACIONES:")
        if recomendaciones:
            for r in recomendaciones:
                print(f"    {r}")
        else:
            print("    ✅ El sistema parece estar bien configurado")
            print("    💡 Si aún falla, prueba generar grupos de un mismo turno")
            print("    💡 O genera por subconjuntos de grupos (2-3 a la vez)")
        
        # ============================================================
        # 6. SUGERENCIA DE ESTRATEGIA
        # ============================================================
        print("\n" + "="*80)
        print("💡 6. ESTRATEGIA SUGERIDA PARA GENERACIÓN")
        print("="*80)
        
        grupos_matutino = [g for g in grupos if g.turno == 'M']
        grupos_vespertino = [g for g in grupos if g.turno == 'V']
        
        print(f"\n    OPCIÓN A: Generar por TURNO separado")
        print(f"       1. Generar primero grupos matutinos ({len(grupos_matutino)} grupos)")
        print(f"          IDs: {[g.id for g in grupos_matutino]}")
        print(f"       2. Luego generar grupos vespertinos ({len(grupos_vespertino)} grupos)")
        print(f"          IDs: {[g.id for g in grupos_vespertino]}")
        
        # Agrupar por carrera
        grupos_por_carrera = defaultdict(list)
        for g in grupos:
            grupos_por_carrera[g.get_carrera_nombre()].append(g)
        
        print(f"\n    OPCIÓN B: Generar por CARRERA")
        for carrera, gs in grupos_por_carrera.items():
            print(f"       {carrera}: {len(gs)} grupos - IDs: {[g.id for g in gs]}")
        
        print(f"\n    OPCIÓN C: Generar de 2-3 grupos a la vez")
        print("       Esto reduce la complejidad del problema OR-Tools")
        print("       y permite que el solver encuentre soluciones más fácilmente")

if __name__ == '__main__':
    diagnostico_completo()
