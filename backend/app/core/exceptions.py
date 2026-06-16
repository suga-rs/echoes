"""Excepciones de dominio."""


class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, mensaje: str, detalles: dict | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles or {}


class PartidaNoEncontradaError(AppError):
    status_code = 404
    code = "partida_no_encontrada"


class PartidaFinalizadaError(AppError):
    status_code = 409
    code = "partida_finalizada"


class LimiteTurnosExcedidoError(AppError):
    status_code = 409
    code = "limite_turnos_excedido"


class LimiteImagenesExcedidoError(AppError):
    status_code = 409
    code = "limite_imagenes_excedido"


class RespuestaLLMInvalidaError(AppError):
    status_code = 502
    code = "respuesta_llm_invalida"


class ContenidoInapropiadoError(AppError):
    status_code = 422
    code = "contenido_inapropiado"


class FoundryError(AppError):
    status_code = 502
    code = "foundry_error"


class UsuarioYaExisteError(AppError):
    status_code = 409
    code = "usuario_ya_existe"


class CredencialesInvalidasError(AppError):
    status_code = 401
    code = "credenciales_invalidas"


class NoAutenticadoError(AppError):
    status_code = 401
    code = "no_autenticado"
