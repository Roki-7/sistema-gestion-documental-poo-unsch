"""Pruebas del modelo. Ejecutar: python -m unittest discover -s tests -v"""
from contextlib import closing
import inspect
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, Mock
import sys

# Permite ejecutar unittest desde la raíz sin instalar el proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codigo"))
import main as s


class ModeloTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.e = s.crear_escenario(self.db)
        self.t, self.d = self.e['tramite'], self.e['documento']
        self.actor, self.jefe = self.e['operador'], self.e['jefe']
        self.proveido = s.flujo.Proveido(id_proveido=1, indicacion='Atender', autor=self.actor)

    def derivacion(self):
        return s.flujo.Derivacion(id_derivacion=1, tramite=self.t, area_remitente=self.e['origen'],
            area_destino=self.e['destino'], documentos=[self.d], proveido=self.proveido)

    def test_formato_expediente(self):
        n = s.registro.NumeroExpediente.generar(self.db, date(2026, 1, 1))
        self.assertRegex(str(n), r'^26[0-9]{6}$')
        with self.assertRaises(ValueError):
            s.registro.NumeroExpediente(valor='2478965')  # El ejemplo de 7 dígitos no satisface AA+6.

    def test_colision_se_reintenta_en_base_de_datos(self):
        with patch.object(s.secrets, 'randbelow', side_effect=[123456, 123456, 654321]):
            a = s.registro.NumeroExpediente.generar(self.db, date(2026, 1, 1))
            b = s.registro.NumeroExpediente.generar(self.db, date(2026, 1, 1))
        self.assertEqual(str(a), '26123456')
        self.assertEqual(str(b), '26654321')

    def test_unicidad_persistente_al_reabrir_base(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = str(Path(carpeta)/'sgd.sqlite3')
            # closing() cierra la conexión; en Windows, un archivo abierto no puede borrarse.
            with closing(sqlite3.connect(ruta)) as db, db, patch.object(s.secrets, 'randbelow', return_value=111111):
                s.registro.NumeroExpediente.generar(db, date(2026, 1, 1))
            with closing(sqlite3.connect(ruta)) as db, db, patch.object(s.secrets, 'randbelow', side_effect=[111111, 222222]):
                nuevo = s.registro.NumeroExpediente.generar(db, date(2026, 1, 1))
                self.assertEqual(str(nuevo), '26222222')

    def test_herencia_expediente_y_folios_calculados(self):
        d2 = s.registro.Documento(modo_registro=s.registro.ModoRegistro.AUTOMATIZADO, cantidad_folios=5, tramite=self.t)
        self.t.agregar_documento(d2, self.actor)
        self.assertIs(d2.numero_expediente, self.d.numero_expediente)
        self.assertEqual(self.t.cantidad_folios, 8)
        with self.assertRaises(AttributeError):
            self.t.cantidad_folios = 100

    def test_no_documento_duplicado_ni_de_otro_tramite(self):
        with self.assertRaises(ValueError):
            self.t.agregar_documento(self.d, self.actor)
        otro = s.crear_escenario(self.db)
        with self.assertRaises(ValueError):
            self.t.agregar_documento(otro['documento'], self.actor)

    def test_sin_alias_de_colecciones(self):
        entrada = [self.actor.roles[0]]
        u = s.seguridad.Usuario(id_usuario=99, nombres='Luis', apellidos='Quispe', correo='luis@example.org',
                      tipo_usuario=s.seguridad.TipoUsuario.INTERNO, roles=entrada)
        entrada.clear()
        self.assertEqual(len(u.roles), 1)
        with self.assertRaises(TypeError):
            self.t.consultar()['asunto'] = 'Alteración'
        self.assertIsInstance(self.t.consultar()['documentos'], tuple)

    def test_folios_rechazan_bool_y_negativos(self):
        for valor in [True, -1, 0]:
            with self.subTest(valor=valor), self.assertRaises((TypeError, ValueError)):
                s.registro.Documento(modo_registro=s.registro.ModoRegistro.MANUAL, cantidad_folios=valor, tramite=self.t)

    def test_permisos_impiden_modificar(self):
        d2 = s.registro.Documento(modo_registro=s.registro.ModoRegistro.MANUAL, cantidad_folios=1, tramite=self.t)
        with self.assertRaises(PermissionError):
            self.t.agregar_documento(d2, self.e['solicitante'])
        self.assertEqual(self.t.cantidad_folios, 3)

    def test_cargo_es_una_instantanea(self):
        cargo = self.t.generar_cargo('Persona natural', 'Correo')
        self.t.agregar_documento(s.registro.Documento(modo_registro=s.registro.ModoRegistro.MANUAL,
            cantidad_folios=2, tramite=self.t), self.actor)
        self.assertEqual(cargo.consultar()['cantidad_folios'], 3)
        self.assertEqual(self.t.cantidad_folios, 5)

    def test_auditoria_persistente_y_sin_reemplazo_de_id(self):
        a = s.seguridad.RegistroAuditoria(id_auditoria=1, usuario=self.actor, accion=s.seguridad.AccionAuditoria.CREACION,
            tipo_registro='Tramite', id_registro_afectado=str(self.d.numero_expediente))
        a.persistir(self.db)
        self.assertEqual(self.db.execute('SELECT accion FROM auditoria').fetchone()[0], 'CREACION')
        with self.assertRaises(sqlite3.IntegrityError):
            a.persistir(self.db)
        self.assertEqual(self.db.execute('SELECT count(*) FROM auditoria').fetchone()[0], 1)

    def test_correccion_exige_motivo_y_conserva_original(self):
        d = self.derivacion()
        tercero = s.flujo.Dependencia(codigo='DEC', nombre='Decanato', jefe=self.jefe)
        with self.assertRaises(ValueError):
            d.corregir(tercero, self.actor, '  ', 2, 1)
        c = d.corregir(tercero, self.actor, 'Destino seleccionado por error', 2, 1)
        self.assertEqual(d.estado, s.flujo.EstadoDerivacion.CORREGIDA)
        self.assertIs(c.consultar()['derivacion_original'], d)
        self.assertEqual(c.consultar()['derivacion_sustituta'].estado, s.flujo.EstadoDerivacion.PENDIENTE)

    def test_derivacion_aceptada_no_se_corrige(self):
        d = self.derivacion()
        d.aceptar(self.actor, self.e['destino'])
        with self.assertRaises(ValueError):
            d.corregir(self.e['origen'], self.actor, 'Error', 2, 1)
        self.assertIs(self.t.consultar()['destinatario'], self.e['destino'])

    def tramite_en(self, dependencia):
        """Crea otro trámite con un documento, que ya está en la dependencia indicada."""
        t = s.registro.Tramite(numero_expediente=s.registro.NumeroExpediente.generar(self.db),
            remitente=self.e['solicitante'], destinatario=dependencia, asunto='Otra solicitud',
            categoria=s.registro.Categoria(codigo='ACA', nombre='Académico'),
            tipo_documento=s.registro.TipoDocumento(codigo='SOL', nombre='Solicitud'),
            prioridad=s.registro.Prioridad(codigo='NOR', nombre='Normal'))
        d = s.registro.Documento(modo_registro=s.registro.ModoRegistro.MANUAL, cantidad_folios=1, tramite=t)
        t.agregar_documento(d, self.actor)
        return t, d

    def test_masivo_agrupa_por_tramite_y_asigna(self):
        _, otro_documento = self.tramite_en(self.e['origen'])
        docs = (self.d, otro_documento)
        ds = s.flujo.derivar_masivamente(docs, self.e['origen'], self.e['destino'], self.proveido, self.actor, 1)
        self.assertEqual(len(ds), 2)
        asignaciones = s.flujo.asignar_masivamente(docs, self.e['origen'], self.actor, self.jefe, 1)
        self.assertTrue(all(a.vigente for a in asignaciones))
        with self.assertRaises(ValueError):
            s.flujo.asignar_masivamente(docs, self.e['origen'], self.actor, self.jefe, 3, asignaciones)
        with self.assertRaises(ValueError):
            s.flujo.derivar_masivamente((self.d, self.d), self.e['origen'], self.e['destino'], self.proveido, self.actor, 4)

    def test_visto_bueno_solo_jefe_y_sin_inconsistencia_de_estado(self):
        self.t.recepcionar(self.actor, 1)
        solicitud, _ = self.t.solicitar_visto_bueno(self.e['destino'], self.actor, 1, 2)
        impostor = s.seguridad.Usuario(id_usuario=80, nombres='Otro', apellidos='Jefe', correo='otro@example.org',
            tipo_usuario=s.seguridad.TipoUsuario.INTERNO, roles=list(self.jefe.roles))
        with self.assertRaises(PermissionError):
            solicitud.resolver(impostor, True, 'Conforme', 3)
        self.assertEqual(self.t.estado, s.flujo.EstadoTramite.PENDIENTE_VISTO_BUENO)
        solicitud.resolver(self.jefe, True, 'Conforme', 3)
        self.assertEqual(self.t.estado, s.flujo.EstadoTramite.EN_ATENCION)
        self.assertEqual(solicitud.estado, s.flujo.EstadoVistoBueno.APROBADO)
        with self.assertRaises(ValueError):
            solicitud.resolver(self.jefe, True, 'Otra vez', 4)

    def test_aprobacion_exige_booleano_real(self):
        self.t.recepcionar(self.actor, 1)
        solicitud, _ = self.t.solicitar_visto_bueno(self.e['destino'], self.actor, 1, 2)
        with self.assertRaises(TypeError):
            solicitud.resolver(self.jefe, 'False', 'Prueba de entrada incorrecta', 3)
        self.assertEqual(solicitud.estado, s.flujo.EstadoVistoBueno.PENDIENTE)
        self.assertEqual(self.t.estado, s.flujo.EstadoTramite.PENDIENTE_VISTO_BUENO)

    def test_transiciones_invalidas_y_finalizacion(self):
        with self.assertRaises(ValueError):
            self.t.cambiar_estado(s.flujo.EstadoTramite.FINALIZADO, self.actor, 1)
        self.t.recepcionar(self.actor, 1)
        with self.assertRaises(ValueError):
            self.t.cambiar_estado(s.flujo.EstadoTramite.OBSERVADO, self.actor, 2, ' ')
        self.t.cambiar_estado(s.flujo.EstadoTramite.FINALIZADO, self.actor, 2)
        with self.assertRaises(ValueError):
            self.t.agregar_documento(s.registro.Documento(modo_registro=s.registro.ModoRegistro.MANUAL,
                cantidad_folios=1, tramite=self.t), self.actor)

    def notificacion(self):
        return s.avisos.Notificacion(id_notificacion=1, tramite=self.t, correo_destinatario='ana@example.org',
            asunto='Recepción', mensaje='Trámite recibido', tipo_evento=s.avisos.TipoEventoNotificacion.RECEPCION_TRAMITE,
            id_evento_origen='evento-1', correo_remitente='sgd@unsch.edu.pe')

    def test_notificacion_fallida_y_reintento(self):
        class CorreoFallido(s.avisos.ServicioCorreo):
            def enviar(self, *args):
                raise OSError('Fallo de transporte')
        n = self.notificacion()
        intento = n.enviar(CorreoFallido(), 1)
        self.assertFalse(intento.aceptado_por_servicio)
        self.assertEqual(n.estado, s.avisos.EstadoEnvio.FALLIDO)
        intento2 = n.enviar(s._CorreoDemo(), 2)
        self.assertTrue(intento2.aceptado_por_servicio)
        self.assertIsNotNone(n.fecha_envio)
        with self.assertRaises(ValueError):
            n.enviar(s._CorreoDemo(), 3)

    def test_no_duplica_notificacion_de_evento(self):
        repo = s._RepositorioDemo()
        gestor = s.avisos.GestorNotificaciones(servicio_correo=s._CorreoDemo(), repositorio=repo)
        gestor.registrar(self.notificacion())
        with self.assertRaises(ValueError):
            gestor.registrar(self.notificacion())

    def test_memorando_hereda_y_valida_dominio(self):
        m = s.avisos.Memorando(modo_registro=s.registro.ModoRegistro.MANUAL, cantidad_folios=1, tramite=self.t,
            correos_destinatarios={'otro@example.org'}, autor=self.actor)
        self.assertIsInstance(m, s.registro.Documento)
        with self.assertRaises(ValueError):
            m.emitir(self.actor, 'unsch.edu.pe')
        self.assertIsNone(m.fecha_emision)

    def test_busca_archivados_sin_desarchivar_y_motivo_obligatorio(self):
        archivador = s.archivos.Archivador(id_archivador=1, nombre='Archivo', dependencia=self.e['destino'])
        self.d.archivar(archivador, self.actor, 1)
        motor = s.archivos.MotorBusqueda(repositorio=s._RepositorioDemo((self.d,)))
        self.assertEqual(motor.buscar(s.archivos.CriterioBusqueda(asunto='CONSTANCIA'), self.actor), (self.d,))
        self.assertEqual(self.d.estado, s.archivos.EstadoDocumento.ARCHIVADO)
        with self.assertRaises(ValueError):
            self.d.desarchivar(self.actor, '', 1)
        registro = self.d.desarchivar(self.actor, 'Revisión', 1)
        self.assertIs(registro.consultar()['archivador_origen'], archivador)
        self.assertIsNone(self.d.archivador)

    def test_fechas_y_setters_publicos(self):
        f = s.informes.FiltroReporte(fecha_desde=date(2026,1,1), fecha_hasta=date(2026,1,31))
        with self.assertRaises(ValueError):
            f.fecha_desde = date(2026,2,1)
        self.assertEqual(f.fecha_desde, date(2026,1,1))
        c = s.archivos.CriterioBusqueda()
        c.numero_expediente = str(self.d.numero_expediente)
        self.assertTrue(c.coincide(self.d))

    def politica(self, modalidad=s.archivos.ModalidadConservacion.TEMPORAL):
        return s.archivos.PoliticaConservacion(id_politica=1, nombre='Política de prueba', referencia_pcda='REFERENCIA-DEMO',
            version='1', modalidad=modalidad, duracion=1 if modalidad is s.archivos.ModalidadConservacion.TEMPORAL else None,
            unidad_plazo=s.archivos.UnidadPlazo.ANIOS if modalidad is s.archivos.ModalidadConservacion.TEMPORAL else None,
            evento_inicio='Fecha de cierre')

    def test_plazo_calendario_y_conservacion_permanente(self):
        p = self.politica()
        self.assertEqual(p.fecha_vencimiento(date(2024,2,29)), date(2025,2,28))
        self.assertFalse(self.politica(s.archivos.ModalidadConservacion.PERMANENTE).plazo_cumplido(date(2000,1,1), date(2099,1,1)))

    def test_eliminar_exige_plazo_autorizacion_y_confirmacion(self):
        archivo = s.registro.ArchivoElectronico(nombre='a.pdf', formato='pdf', ruta_almacenamiento='a.pdf')
        self.d.adjuntar_archivo(archivo, self.actor)
        self.d.archivar(s.archivos.Archivador(id_archivador=1, nombre='Archivo', dependencia=self.e['origen']),
            self.actor, 1, self.politica(), date(2020,1,1))
        with self.assertRaises(PermissionError):
            self.d.solicitar_eliminacion(self.jefe, False)
        self.d.solicitar_eliminacion(self.jefe, True, date(2022,1,1))
        with self.assertRaises(ValueError):
            self.d.confirmar_eliminacion(self.jefe)
        archivo.registrar_eliminacion(self.d, self.jefe, 1, 'Confirmado por TI', s.archivos.ResultadoEliminacion.CONFIRMADA)
        self.d.confirmar_eliminacion(self.jefe)
        self.assertEqual(self.d.estado, s.archivos.EstadoDocumento.ELIMINADO)

    def test_lectura_no_sale_de_raiz(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo = s.registro.ArchivoElectronico(nombre='a.pdf', formato='pdf', ruta_almacenamiento='/fuera/a.pdf')
            with self.assertRaises(ValueError):
                archivo.leer(Path(directorio))

    def test_reporte_personaliza_y_no_admite_columnas_inexistentes(self):
        r = s.informes.ReporteEstadoTramites(titulo='Estado', filtros=s.informes.FiltroReporte(), repositorio=s._RepositorioDemo((self.d,)))
        r.personalizar(('estado','cantidad'), ('cantidad','estado'))
        filas = r.generar(self.actor).consultar()['filas']
        self.assertEqual(list(filas[0]), ['cantidad','estado'])
        r.personalizar(('inventada',))
        with self.assertRaises(ValueError):
            r.generar(self.actor)

    def test_carga_cuenta_tramites_sin_duplicarlos(self):
        segundo = s.registro.Documento(modo_registro=s.registro.ModoRegistro.MANUAL, cantidad_folios=1, tramite=self.t)
        repo = s._RepositorioDemo((self.d, segundo))
        r = s.informes.ReporteCargaTrabajo(titulo='Carga', filtros=s.informes.FiltroReporte(), repositorio=repo,
            agrupar_por=s.informes.AgrupacionCarga.DEPENDENCIA, unidad_carga=s.informes.UnidadCarga.TRAMITES)
        self.assertEqual(r.generar(self.actor).consultar()['filas'][0]['cantidad'], 1)

    def test_tiempos_exigen_calendario_institucional(self):
        r = s.informes.ReporteTiemposRespuesta(titulo='Tiempo', filtros=s.informes.FiltroReporte(), repositorio=s._RepositorioDemo((self.d,)),
            evento_inicio=s.informes.EventoMedicion.REGISTRO, evento_fin=s.informes.EventoMedicion.RECEPCION,
            unidad_tiempo=s.informes.UnidadTiempo.MINUTOS, usa_tiempo_habil=True)
        with self.assertRaises(ValueError):
            r.generar(self.actor)

    def test_programacion_avanza_y_no_repite(self):
        r = s.informes.ReporteEstadoTramites(titulo='Estado', filtros=s.informes.FiltroReporte(), repositorio=s._RepositorioDemo((self.d,)))
        p = s.informes.ProgramacionReporte(id_programacion=1, reporte=r, frecuencia=s.informes.FrecuenciaReporte.DIARIA,
            zona_horaria='America/Lima', proxima_ejecucion=s.seguridad.ahora()-timedelta(days=2), creada_por=self.actor, activa=True)
        instante = s.seguridad.ahora()
        self.assertIsNotNone(p.ejecutar_si_corresponde(instante))
        self.assertGreater(p.proxima_ejecucion, instante)
        self.assertIsNone(p.ejecutar_si_corresponde(instante))

    def test_exportaciones_son_excel_y_pdf_reales(self):
        resultado = s.informes.ReporteEstadoTramites(titulo='Estado', filtros=s.informes.FiltroReporte(),
            repositorio=s._RepositorioDemo((self.d,))).generar(self.actor)
        with tempfile.TemporaryDirectory() as directorio:
            excel = s.informes.ExportadorExcel().exportar(resultado, Path(directorio)/'r.xlsx')
            pdf = s.informes.ExportadorPDF().exportar(resultado, Path(directorio)/'r.pdf')
            self.assertEqual(excel.read_bytes()[:2], b'PK')
            self.assertEqual(pdf.read_bytes()[:4], b'%PDF')

    def test_interfaces_y_clase_abstracta(self):
        for cls in [s.avisos.ServicioCorreo,s.servicios.ServicioValidacionFirma,s.servicios.ServicioInteroperabilidad,s.informes.ExportadorReporte,s.informes.Reporte]:
            self.assertTrue(inspect.isabstract(cls))
        self.assertTrue(issubclass(s.servicios.AdaptadorPIDE, s.servicios.ServicioInteroperabilidad))
        self.assertTrue(issubclass(s.informes.ExportadorPDF, s.informes.ExportadorReporte))

    def archivo(self):
        return s.registro.ArchivoElectronico(nombre='a.pdf', formato='pdf', ruta_almacenamiento='a.pdf')

    def test_firma_no_confunde_falta_de_firmas_con_validez(self):
        a = s.servicios.AdaptadorValidacionFirma(direccion_servicio='https://demo.invalid/firma')
        sin_firmas = a.validar(self.archivo(), b'bytes', 1,
            lambda *args: {'consulta_completada':True, 'firmas':[]})
        self.assertFalse(sin_firmas.es_valida())
        valida = a.validar(self.archivo(), b'bytes', 2,
            lambda *args: {'consulta_completada':True, 'firmas':[{'referencia':'f1','estado':'VALIDA'}]})
        self.assertTrue(valida.es_valida())
        self.assertFalse(valida.corresponde_al_contenido(b'otros bytes'))
        self.assertTrue(valida.corresponde_al_contenido(b'bytes'))
        with self.assertRaises(RuntimeError):
            a.validar(self.archivo(), b'bytes', 3)

    def test_respuesta_de_firma_invalida_no_se_presenta_como_valida(self):
        a = s.servicios.AdaptadorValidacionFirma(direccion_servicio='https://demo.invalid/firma')
        resultado = a.validar(self.archivo(), b'bytes', 1,
            lambda *args: {'consulta_completada':True, 'firmas':[{'referencia':'f','estado':'NO_DEFINIDO'}]})
        self.assertFalse(resultado.es_valida())
        self.assertFalse(resultado.consultar()['consulta_completada'])

    def intercambio(self):
        return s.servicios.IntercambioDocumentario(id_intercambio=1, id_correlacion='abc', direccion=s.servicios.DireccionIntercambio.ENVIO,
            documento=self.d, entidad_origen=s.servicios.EntidadInteroperante(codigo='UNSCH', nombre='Universidad'),
            entidad_destino=s.servicios.EntidadInteroperante(codigo='EXT', nombre='Entidad externa'))

    def test_intercambio_confirma_solo_su_correlacion(self):
        a = s.servicios.AdaptadorPIDE(direccion_servicio='https://demo.invalid/pide')
        intercambio = self.intercambio()
        a.intercambiar(intercambio, lambda *args: {'id_correlacion':'otra','confirmado':True,'referencia':'123'})
        self.assertEqual(intercambio.estado, s.servicios.EstadoIntercambio.INDETERMINADO)
        otro = self.intercambio()
        a.intercambiar(otro, lambda *args: {'id_correlacion':'abc','confirmado':True,'referencia':'123'})
        self.assertEqual(otro.estado, s.servicios.EstadoIntercambio.CONFIRMADO)
        self.assertEqual(otro.referencia_externa, '123')
        with self.assertRaises(ValueError):
            a.intercambiar(otro, lambda *args: {})


    def test_revision_numero_expediente_compara_su_valor(self):
        uno = s.registro.NumeroExpediente(valor='26000001')
        otro = s.registro.NumeroExpediente(valor='26000001')
        distinto = s.registro.NumeroExpediente(valor='26000002')
        self.assertEqual(uno, otro)
        self.assertEqual(len({uno, otro, distinto}), 2)
        self.assertNotEqual(uno, '26000001')

    def test_revision_preparar_base_no_confirma_transaccion_ajena(self):
        self.db.execute('CREATE TABLE auxiliar (valor TEXT)')
        self.db.execute("INSERT INTO auxiliar VALUES ('pendiente')")
        s.seguridad.preparar_base(self.db)
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()
        self.assertEqual(self.db.execute('SELECT count(*) FROM auxiliar').fetchone()[0], 0)

    def test_revision_reserva_de_expediente_respeta_rollback_exterior(self):
        with closing(sqlite3.connect(':memory:')) as db:
            s.seguridad.preparar_base(db)
            db.execute('CREATE TABLE auxiliar (valor TEXT)')
            db.execute("INSERT INTO auxiliar VALUES ('pendiente')")
            with patch.object(s.secrets, 'randbelow', return_value=123456):
                s.registro.NumeroExpediente.generar(db, date(2026,1,1))
            self.assertTrue(db.in_transaction)
            db.rollback()
            self.assertEqual(db.execute('SELECT count(*) FROM auxiliar').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM expedientes').fetchone()[0], 0)

    def test_revision_auditoria_no_confirma_ni_borra_transaccion_ajena(self):
        s.seguridad.preparar_base(self.db)
        self.db.execute('CREATE TABLE auxiliar (valor TEXT)')
        self.db.execute("INSERT INTO auxiliar VALUES ('pendiente')")
        evento = s.seguridad.RegistroAuditoria(id_auditoria=91, usuario=self.actor,
            accion=s.seguridad.AccionAuditoria.ACCESO, tipo_registro='Tramite',
            id_registro_afectado=str(self.d.numero_expediente))
        evento.persistir(self.db)
        with self.assertRaises(sqlite3.IntegrityError):
            evento.persistir(self.db)
        self.assertEqual(self.db.execute('SELECT count(*) FROM auxiliar').fetchone()[0], 1)
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()
        self.assertEqual(self.db.execute('SELECT count(*) FROM auditoria').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM auxiliar').fetchone()[0], 0)

    def test_revision_cambio_inicial_conserva_fecha_de_recepcion(self):
        cambio = self.t.cambiar_estado(s.flujo.EstadoTramite.EN_ATENCION, self.actor, 1)
        fecha = self.t.consultar()['fecha_recepcion']
        self.assertEqual(fecha, cambio.consultar()['fecha_hora'])
        self.t.cambiar_estado(s.flujo.EstadoTramite.OBSERVADO, self.actor, 2, 'Falta subsanar')
        self.t.cambiar_estado(s.flujo.EstadoTramite.EN_ATENCION, self.actor, 3)
        self.assertEqual(self.t.consultar()['fecha_recepcion'], fecha)
        with self.assertRaises(ValueError):
            self.t.recepcionar(self.actor, 4)

    def test_revision_retomar_atencion_no_notifica_otra_recepcion(self):
        repo = s._RepositorioDemo()
        gestor = s.avisos.GestorNotificaciones(servicio_correo=s._CorreoDemo(), repositorio=repo)
        for indice, anterior in enumerate([s.flujo.EstadoTramite.OBSERVADO,
                                          s.flujo.EstadoTramite.PENDIENTE_VISTO_BUENO], 1):
            cambio = s.flujo.CambioEstadoTramite(id_cambio=indice, tramite=self.t,
                estado_anterior=anterior, estado_nuevo=s.flujo.EstadoTramite.EN_ATENCION,
                actor=self.actor)
            resultado = s.avisos.notificar_cambio(cambio, gestor, 'sgd@unsch.edu.pe', indice)
            self.assertIsNone(resultado)
        self.assertFalse(repo.notificaciones)
        self.assertFalse(repo.intentos)

    def test_revision_id_de_intento_se_valida_antes_del_envio(self):
        correo = Mock(spec=s.avisos.ServicioCorreo)
        correo.enviar.return_value = 'id-proveedor'
        n = self.notificacion()
        for invalido in [-1, True, '1']:
            with self.subTest(invalido=invalido), self.assertRaises((TypeError,ValueError)):
                n.enviar(correo, invalido)
        correo.enviar.assert_not_called()
        self.assertEqual(n.estado, s.avisos.EstadoEnvio.PENDIENTE)

    def test_revision_resultado_no_comparte_diccionarios_de_entrada(self):
        filas = [{'grupo':'A', 'detalle':{'total':1}}]
        resultado = s.informes.ResultadoReporte(fecha_generacion=s.seguridad.ahora(),
            fecha_corte=s.seguridad.ahora()-timedelta(seconds=1), solicitante=self.actor,
            origen_ejecucion=s.informes.OrigenEjecucion.MANUAL,
            parametros_aplicados={'titulo':'Prueba'}, filas=filas)
        filas[0]['grupo'] = 'CAMBIADO'
        filas[0]['detalle']['total'] = 99
        self.assertEqual(resultado.consultar()['filas'][0]['grupo'], 'A')
        self.assertEqual(resultado.consultar()['filas'][0]['detalle']['total'], 1)

    def test_revision_reporte_conserva_parametros_especificos(self):
        repo = s._RepositorioDemo((self.d,))
        carga = s.informes.ReporteCargaTrabajo(titulo='Carga', filtros=s.informes.FiltroReporte(),
            repositorio=repo, agrupar_por=s.informes.AgrupacionCarga.DEPENDENCIA,
            unidad_carga=s.informes.UnidadCarga.TRAMITES)
        parametros = carga.generar(self.actor).consultar()['parametros_aplicados']
        self.assertEqual(parametros['agrupar_por'], 'dependencia')
        self.assertEqual(parametros['unidad_carga'], 'tramite')
        tiempos = s.informes.ReporteTiemposRespuesta(titulo='Tiempo', filtros=s.informes.FiltroReporte(),
            repositorio=repo, evento_inicio=s.informes.EventoMedicion.REGISTRO,
            evento_fin=s.informes.EventoMedicion.RECEPCION, unidad_tiempo=s.informes.UnidadTiempo.MINUTOS,
            usa_tiempo_habil=False)
        parametros = tiempos.generar(self.actor).consultar()['parametros_aplicados']
        self.assertEqual(parametros['evento_inicio'], 'registro')
        self.assertEqual(parametros['evento_fin'], 'recepcion')
        self.assertEqual(parametros['unidad_tiempo'], 'MINUTOS')
        self.assertFalse(parametros['usa_tiempo_habil'])

    def test_revision_calendario_habil_llega_al_reporte_programado(self):
        corte = s.seguridad.ahora()
        class RepositorioEventos:
            def consultar(self, tipo, filtros, fecha_corte):
                return [{'expediente':'26000001','registro':corte-timedelta(hours=2),
                         'recepcion':corte-timedelta(hours=1)}]
        reporte = s.informes.ReporteTiemposRespuesta(titulo='Tiempo', filtros=s.informes.FiltroReporte(),
            repositorio=RepositorioEventos(), evento_inicio=s.informes.EventoMedicion.REGISTRO,
            evento_fin=s.informes.EventoMedicion.RECEPCION, unidad_tiempo=s.informes.UnidadTiempo.MINUTOS,
            usa_tiempo_habil=True)
        programa = s.informes.ProgramacionReporte(id_programacion=1, reporte=reporte,
            frecuencia=s.informes.FrecuenciaReporte.DIARIA, zona_horaria='America/Lima',
            proxima_ejecucion=corte-timedelta(minutes=1), creada_por=self.actor, activa=True)
        calendario = Mock(return_value=120.0)
        resultado = programa.ejecutar_si_corresponde(corte, calendario_habil=calendario)
        self.assertEqual(resultado.consultar()['filas'][0]['duracion'], 2)
        calendario.assert_called_once()

    def test_revision_constructor_de_reporte_valida_su_personalizacion(self):
        for columnas, orden in [(('estado','estado'),()), (('estado',),('cantidad',))]:
            with self.subTest(columnas=columnas), self.assertRaises(ValueError):
                s.informes.ReporteEstadoTramites(titulo='Estado', filtros=s.informes.FiltroReporte(),
                    repositorio=s._RepositorioDemo(), columnas_seleccionadas=columnas, orden_presentacion=orden)

    def test_revision_filtro_no_confunde_fecha_con_fecha_hora(self):
        with self.assertRaises(TypeError):
            s.informes.FiltroReporte(fecha_desde=s.seguridad.ahora())
        with self.assertRaises(TypeError):
            s.archivos.CriterioBusqueda(fecha_hasta=s.seguridad.ahora())

    def test_revision_tiempos_de_espera_deben_ser_finitos(self):
        for adaptador in [s.servicios.AdaptadorPIDE,s.servicios.AdaptadorValidacionFirma]:
            for valor in [float('nan'),float('inf')]:
                with self.subTest(adaptador=adaptador,valor=valor), self.assertRaises(TypeError):
                    adaptador(direccion_servicio='https://demo.invalid/servicio',tiempo_espera_segundos=valor)

    def test_revision_rearchivar_conserva_politica_y_fecha_de_origen(self):
        archivador = s.archivos.Archivador(id_archivador=1, nombre='Archivo', dependencia=self.e['origen'])
        politica = self.politica()
        inicio = date(2020,1,1)
        self.d.archivar(archivador,self.actor,1,politica,inicio)
        self.d.desarchivar(self.actor,'Revisión',1)
        registro = self.d.archivar(archivador,self.actor,2)
        self.assertIs(self.d.consultar()['politica_conservacion'], politica)
        self.assertIs(registro.consultar()['politica_aplicada'], politica)
        self.assertEqual(self.d.consultar()['fecha_inicio_computo'], inicio)

    def test_revision_archivamiento_invalido_no_cambia_el_estado(self):
        archivador = s.archivos.Archivador(id_archivador=1, nombre='Archivo', dependencia=self.e['origen'])
        with self.assertRaises(TypeError):
            self.d.archivar(archivador,self.actor,1,self.politica(),'2020-01-01')
        self.assertEqual(self.d.estado,s.archivos.EstadoDocumento.ACTIVO)
        self.assertIsNone(self.d.archivador)

    def test_revision_jefatura_externa_se_rechaza_tambien_en_constructor(self):
        with self.assertRaises(ValueError):
            s.flujo.Dependencia(codigo='X',nombre='Dependencia',jefe=self.e['solicitante'])

    def test_revision_derivacion_no_avanza_despues_de_finalizar(self):
        derivacion = self.derivacion()
        self.t.recepcionar(self.actor,1)
        self.t.cambiar_estado(s.flujo.EstadoTramite.FINALIZADO,self.actor,2)
        with self.assertRaises(ValueError):
            derivacion.aceptar(self.actor,self.e['destino'])
        self.assertEqual(derivacion.estado,s.flujo.EstadoDerivacion.PENDIENTE)
        self.assertIsNone(derivacion.consultar()['fecha_hora_aceptacion'])
        with self.assertRaises(ValueError):
            self.derivacion()

    def test_revision_derivacion_espera_resolucion_de_visto_bueno(self):
        derivacion = self.derivacion()
        self.t.recepcionar(self.actor,1)
        self.t.solicitar_visto_bueno(self.e['destino'],self.actor,1,2)
        with self.assertRaises(ValueError):
            derivacion.aceptar(self.actor,self.e['destino'])
        self.assertEqual(derivacion.estado,s.flujo.EstadoDerivacion.PENDIENTE)
        with self.assertRaises(ValueError):
            self.derivacion()


    def test_revision_documento_pendiente_conserva_archivador_al_reconstruir(self):
        archivador = s.archivos.Archivador(id_archivador=1, nombre='Archivo', dependencia=self.e['origen'])
        politica = self.politica()
        self.d.archivar(archivador,self.actor,1,politica,date(2020,1,1))
        self.d.solicitar_eliminacion(self.jefe,True,date(2022,1,1))
        datos = dict(self.d.consultar())
        datos['archivos'] = list(datos['archivos'])
        reconstruido = s.registro.Documento(**datos)
        self.assertIs(reconstruido.archivador, archivador)
        self.assertEqual(reconstruido.estado,s.archivos.EstadoDocumento.ELIMINACION_PENDIENTE)


    # ── Correcciones de la revisión ──────────────────────────────────────

    def test_cambio_de_jefatura_no_bloquea_el_visto_bueno(self):
        self.t.recepcionar(self.actor, 1)
        solicitud, _ = self.t.solicitar_visto_bueno(self.e['destino'], self.actor, 1, 2)
        nuevo = s.seguridad.Usuario(id_usuario=70, nombres='Nuevo', apellidos='Jefe',
            correo='nuevo@unsch.edu.pe', tipo_usuario=s.seguridad.TipoUsuario.INTERNO,
            roles=list(self.jefe.roles))
        self.e['destino'].designar_jefe(nuevo, self.jefe)
        with self.assertRaises(PermissionError):
            solicitud.resolver(self.jefe, True, 'Ya no soy jefe', 3)
        solicitud.resolver(nuevo, True, 'Conforme', 3)
        datos = solicitud.consultar()
        self.assertIs(datos['jefe_destinatario'], self.jefe)
        self.assertIs(datos['resuelto_por'], nuevo)
        self.assertEqual(self.t.estado, s.flujo.EstadoTramite.EN_ATENCION)

    def test_designar_jefe_exige_permiso_y_usuario(self):
        with self.assertRaises(PermissionError):
            self.e['destino'].designar_jefe(self.actor, self.actor)
        with self.assertRaises(TypeError):
            self.e['destino'].designar_jefe('Jefe', self.jefe)
        self.assertIs(self.e['destino'].consultar()['jefe'], self.jefe)

    def test_solo_la_dependencia_que_tiene_el_tramite_deriva(self):
        ajena = s.flujo.Dependencia(codigo='AJ', nombre='Dependencia ajena')
        with self.assertRaises(PermissionError):
            s.flujo.derivar_masivamente((self.d,), ajena, self.e['destino'], self.proveido, self.actor, 1)
        with self.assertRaises(PermissionError):
            s.flujo.derivar_masivamente((self.d,), self.e['origen'], self.e['destino'],
                                        self.proveido, self.e['solicitante'], 1)
        configuracion = s.flujo.ConfiguracionDerivacion(id_configuracion=1, nombre='Académicos',
            area_inicio=self.e['destino'], aplica_a_externos=True, aplica_a_academicos=True)
        with self.assertRaises(PermissionError):
            configuracion.derivar(self.t, ajena, self.proveido, 1, self.actor)
        derivacion = configuracion.derivar(self.t, self.e['origen'], self.proveido, 1, self.actor)
        self.assertIs(derivacion.consultar()['area_destino'], self.e['destino'])

    def test_documento_solo_fisico_puede_eliminarse(self):
        archivador = s.archivos.Archivador(id_archivador=1, nombre='Archivo', dependencia=self.e['origen'])
        self.d.archivar(archivador, self.actor, 1, self.politica(), date(2020, 1, 1))
        self.d.solicitar_eliminacion(self.jefe, True, date(2022, 1, 1))
        self.d.confirmar_eliminacion(self.jefe)
        self.assertEqual(self.d.estado, s.archivos.EstadoDocumento.ELIMINADO)
        self.assertIsNone(self.d.archivador)

    def test_busqueda_y_cargo_usan_la_hora_de_peru(self):
        # 1 de noviembre, 21:00 en Lima = 2 de noviembre, 02:00 UTC.
        registro = datetime(2026, 11, 2, 2, 0, tzinfo=timezone.utc)
        t = s.registro.Tramite(numero_expediente=s.registro.NumeroExpediente.generar(self.db),
            fecha_hora_registro=registro, remitente=self.e['solicitante'], destinatario=self.e['origen'],
            asunto='Nocturno', categoria=s.registro.Categoria(codigo='A', nombre='A'),
            tipo_documento=s.registro.TipoDocumento(codigo='A', nombre='A'),
            prioridad=s.registro.Prioridad(codigo='A', nombre='A'))
        d = s.registro.Documento(modo_registro=s.registro.ModoRegistro.MANUAL, cantidad_folios=1, tramite=t)
        dia = date(2026, 11, 1)
        self.assertTrue(s.archivos.CriterioBusqueda(fecha_desde=dia, fecha_hasta=dia).coincide(d))
        cargo = s.registro.Cargo(nombres_apellidos_solicitante='Ana', numero_expediente='26000001',
            fecha_hora_registro=registro, cantidad_folios=1, entidad='Persona natural',
            oficina_que_recibe='Mesa de partes', asunto='x', medio_notificacion='Correo')
        self.assertIn('01/11/2026 21:00', cargo.texto())

    def test_auditoria_asigna_identificadores_y_persiste(self):
        Accion = s.seguridad.AccionAuditoria
        primero = s.seguridad.RegistroAuditoria.registrar(self.db, self.actor, Accion.CREACION,
            'Tramite', str(self.d.numero_expediente))
        segundo = s.seguridad.RegistroAuditoria.registrar(self.db, self.actor, Accion.ACCESO,
            'Documento', str(self.d.numero_expediente), 'Búsqueda')
        self.assertEqual((primero.id_auditoria, segundo.id_auditoria), (1, 2))
        filas = self.db.execute('SELECT id, usuario_id, accion FROM auditoria ORDER BY id').fetchall()
        self.assertEqual(filas, [(1, 1, 'CREACION'), (2, 1, 'ACCESO')])

    def test_reporte_exige_solicitante_autorizado(self):
        r = s.informes.ReporteEstadoTramites(titulo='Estado', filtros=s.informes.FiltroReporte(),
            repositorio=s._RepositorioDemo((self.d,)))
        with self.assertRaises(TypeError):
            r.generar()
        with self.assertRaises(TypeError):
            r.generar(None)
        with self.assertRaises(PermissionError):
            r.generar(self.e['solicitante'])

    def test_excel_guarda_formulas_como_texto_y_todas_las_columnas(self):
        from openpyxl import load_workbook
        resultado = s.informes.ResultadoReporte(fecha_generacion=s.seguridad.ahora(),
            fecha_corte=s.seguridad.ahora() - timedelta(seconds=1), solicitante=self.actor,
            origen_ejecucion=s.informes.OrigenEjecucion.MANUAL, parametros_aplicados={'titulo': 'X'},
            filas=[{'asunto': '=HYPERLINK("x")'}, {'asunto': 'normal', 'extra': 1}])
        with tempfile.TemporaryDirectory() as directorio:
            ruta = s.informes.ExportadorExcel().exportar(resultado, Path(directorio)/'r.xlsx')
            libro = load_workbook(ruta)
            hoja = libro.active
            self.assertEqual([c.value for c in hoja[1]], ['asunto', 'extra'])
            self.assertEqual(hoja['A2'].value, '=HYPERLINK("x")')
            self.assertEqual(hoja['A2'].data_type, 's')
            libro.close()


if __name__ == '__main__':
    unittest.main()
