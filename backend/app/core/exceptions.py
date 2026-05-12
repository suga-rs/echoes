"""Excepciones de dominio."""


class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, mensaje: str, detalles: dict | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles or {}


class PartidaNoEncontrada(AppError):
    status_code = 404
    code = "partida_no_encontrada"


class PartidaFinalizada(AppError):
    status_code = 409
    code = "partida_finalizada"


class LimiteTurnosExcedido(AppError):
    status_code = 409
    code = "limite_turnos_excedido"


class RespuestaLLMInvalida(AppError):
    status_code = 502
    code = "respuesta_llm_invalida"


class ContenidoInapropiado(AppError):
    status_code = 422
    code = "contenido_inapropiado"


class FoundryError(AppError):
    status_code = 502
    code = "foundry_error"
