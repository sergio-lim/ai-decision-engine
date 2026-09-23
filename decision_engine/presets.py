"""Question presets for Jev.

Each preset is a dict of typed questions (``choice``, ``noul``, ``score``).
The model returns structured answers plus per-label probabilities — no
regex, no "parse the LLM's English".
"""

from __future__ import annotations

from typing import Any

REPLY_CLASSIFY_QUESTIONS: dict[str, Any] = {
    "tipo": {
        "type": "choice",
        "instructions": (
            "What kind of inbound recruiter/company reply is this, after a "
            "candidate sent a job application?"
        ),
        "criteria": {
            "acuse_simple": (
                "Solo acusa recibo/agradece/dice que compartira o revisara el "
                "perfil. No pide ni propone nada."
            ),
            "requiere_decision": (
                "Pide algo, propone entrevista/llamada, habla de "
                "salario/legal/visa/formulario/prueba, o es rechazo/bounce."
            ),
        },
    },
    "pide_info": {
        "type": "noul",
        "instructions": (
            "Does the message ask the candidate for information, documents, "
            "or answers to questions?"
        ),
        "criteria": {
            "true": "Asks for information, documents, dates, or answers.",
            "false": "Does not request anything from the candidate.",
        },
    },
    "propone_entrevista": {
        "type": "noul",
        "instructions": (
            "Does the message propose an interview, call, meeting, or a slot "
            "to schedule one?"
        ),
        "criteria": {
            "true": "Proposes an interview, call, meeting, or scheduling.",
            "false": "Does not propose a meeting or interview.",
        },
    },
    "menciona_salario": {
        "type": "noul",
        "instructions": (
            "Does the message mention salary, compensation, rate, or "
            "pay expectations?"
        ),
        "criteria": {
            "true": "Mentions salary, compensation, rate, or pretensión salarial.",
            "false": "Does not talk about pay.",
        },
    },
    "requiere_work_auth": {
        "type": "noul",
        "instructions": (
            "Does the message ask about work authorization, visa, "
            "sponsorship, or legal right to work?"
        ),
        "criteria": {
            "true": "Asks about visa, sponsorship, or work authorization.",
            "false": "Does not mention legal right to work.",
        },
    },
    "es_rechazo": {
        "type": "noul",
        "instructions": "Is this a rejection or a notice that the process stops?",
        "criteria": {
            "true": "Rejects the application or says the process will not continue.",
            "false": "Not a rejection.",
        },
    },
    "es_bounce": {
        "type": "noul",
        "instructions": (
            "Is this a delivery failure, bounce, mailer-daemon, or unknown address?"
        ),
        "criteria": {
            "true": "Bounce, mailer-daemon, address not found, or delivery failure.",
            "false": "Not a bounce or delivery error.",
        },
    },
}

TICKET_TRIAGE_QUESTIONS: dict[str, Any] = {
    "categoria": {
        "type": "choice",
        "instructions": "What kind of support ticket is this?",
        "criteria": {
            "bug": "Something is broken, incorrect, or returning an error.",
            "request": "The user wants a change, access, or a new capability.",
            "question": "The user is asking how something works.",
        },
    },
    "urgencia": {
        "type": "score",
        "instructions": "How urgent is this ticket for the user or the system?",
        "criteria": [
            "No user impact; can wait for the next planning cycle.",
            "Degraded experience, but a workaround exists.",
            "Blocking production, data loss, or a security incident.",
        ],
    },
    "es_incidente_seguridad": {
        "type": "noul",
        "instructions": "Is this a security incident rather than a normal ticket?",
        "criteria": {
            "true": "Mentions a breach, leak, unauthorized access, or exploit.",
            "false": "No security-incident language.",
        },
    },
}

PRESETS: dict[str, dict[str, Any]] = {
    "reply_classify": REPLY_CLASSIFY_QUESTIONS,
    "ticket_triage": TICKET_TRIAGE_QUESTIONS,
}

FLAG_KEYS: tuple[str, ...] = (
    "pide_info",
    "propone_entrevista",
    "menciona_salario",
    "requiere_work_auth",
    "es_rechazo",
    "es_bounce",
)
