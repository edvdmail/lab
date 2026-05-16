# extractors/pdf_unlock.py
import io
import pikepdf

def is_pdf_encrypted(file_bytes: bytes) -> bool:
    """Verifica si un PDF está protegido con contraseña"""
    try:
        with pikepdf.open(io.BytesIO(file_bytes)):
            return False
    except pikepdf.PasswordError:
        return True
    except Exception:
        return False


def unlock_pdf(file_bytes: bytes, password: str) -> bytes | None:
    """Intenta desbloquear un PDF con una contraseña"""
    try:
        buf_out = io.BytesIO()
        with pikepdf.open(io.BytesIO(file_bytes), password=password) as pdf:
            pdf.save(buf_out)
        return buf_out.getvalue()
    except pikepdf.PasswordError:
        return None
    except Exception:
        return None


def unlock_pdf_with_fallbacks(file_bytes: bytes, identificacion: str) -> bytes | None:
    """Intenta desbloquear usando la identificación del paciente"""
    if not identificacion or not identificacion.strip():
        return None

    # Intento principal
    unlocked = unlock_pdf(file_bytes, identificacion.strip())
    if unlocked:
        return unlocked

    # Variante sin ceros a la izquierda
    stripped = identificacion.strip().lstrip("0")
    if stripped and stripped != identificacion.strip():
        unlocked = unlock_pdf(file_bytes, stripped)
        if unlocked:
            return unlocked

    return None