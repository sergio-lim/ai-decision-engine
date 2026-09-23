# Benchmark: regex baseline vs Jev

Same 16 labeled recruiter replies. The baseline is a thanks-first keyword regex. Jev is a typed decision model with confidence routing.

## Summary

- Cases: **16**
- Regex accuracy: **75.0%** (errors: [9, 10, 13, 16])
- Jev accuracy: **100.0%** (errors: none)
- Jev total cost: **$0.000517**
- Jev mean latency: **1.42s** (n=16)

## Cases

| id | label | regex | jev | jev conf | route | flags | cost | latency |
|---:|:------|:------|:----|-------:|:------|:------|-----:|--------:|
| 1 | simple_ack | simple_ack | simple_ack | 1.00 | simple_ack | — | $0.000032 | 2.86s |
| 2 | simple_ack | simple_ack | simple_ack | 1.00 | simple_ack | — | $0.000033 | 0.38s |
| 3 | simple_ack | simple_ack | simple_ack | 1.00 | simple_ack | — | $0.000032 | 0.48s |
| 4 | simple_ack | simple_ack | simple_ack | 0.98 | simple_ack | — | $0.000033 | 1.88s |
| 5 | simple_ack | simple_ack | simple_ack | 1.00 | simple_ack | — | $0.000032 | 0.35s |
| 6 | simple_ack | simple_ack | simple_ack | 1.00 | simple_ack | — | $0.000032 | 0.51s |
| 7 | simple_ack | simple_ack | simple_ack | 1.00 | simple_ack | — | $0.000032 | 2.54s |
| 8 | simple_ack | simple_ack | simple_ack | 1.00 | simple_ack | — | $0.000032 | 3.37s |
| 9 | needs_judgment | simple_ack | needs_judgment | 1.00 | needs_judgment | pide_info,menciona_salario | $0.000032 | 2.55s |
| 10 | needs_judgment | simple_ack | needs_judgment | 1.00 | needs_judgment | propone_entrevista | $0.000032 | 0.58s |
| 11 | needs_judgment | needs_judgment | needs_judgment | 1.00 | needs_judgment | es_rechazo | $0.000032 | 1.67s |
| 12 | needs_judgment | needs_judgment | needs_judgment | 1.00 | needs_judgment | pide_info,requiere_work_auth | $0.000032 | 1.08s |
| 13 | needs_judgment | simple_ack | needs_judgment | 1.00 | needs_judgment | es_bounce | $0.000032 | 0.40s |
| 14 | needs_judgment | needs_judgment | needs_judgment | 1.00 | needs_judgment | pide_info | $0.000032 | 1.79s |
| 15 | needs_judgment | needs_judgment | needs_judgment | 1.00 | needs_judgment | pide_info | $0.000032 | 0.43s |
| 16 | needs_judgment | simple_ack | needs_judgment | 1.00 | needs_judgment | pide_info,menciona_salario | $0.000032 | 1.80s |

## Texts

- **#1** `simple_ack` — Hi Sergio, thanks for sending your CV. I'll share your profile with our talent team.
- **#2** `simple_ack` — Hola Sergio, muchas gracias por compartir tus datos. Estaré pasando tu perfil al equipo de Talento.
- **#3** `simple_ack` — Gracias por tu correo, quedo atento a cualquier novedad.
- **#4** `simple_ack` — Thanks for reaching out - I reviewed your profile and will get back to you if there's a fit.
- **#5** `simple_ack` — Recibido. Lo reviso y te comento.
- **#6** `simple_ack` — Thank you for your interest. Your application has been received.
- **#7** `simple_ack` — Hola Sergio, recibido! Cualquier novedad te aviso.
- **#8** `simple_ack` — Thanks! I'll pass this along to the hiring manager and let you know.
- **#9** `needs_judgment` — Thanks for your interest. Could you share your salary expectations for this role?
- **#10** `needs_judgment` — Hola Sergio, te comparto mi agenda para agendar una entrevista.
- **#11** `needs_judgment` — Unfortunately we are not moving forward with your application at this time.
- **#12** `needs_judgment` — Hi Sergio, are you authorized to work in Argentina? Do you require sponsorship?
- **#13** `needs_judgment` — Mail Delivery Subsystem: Address not found. Your message wasn't delivered.
- **#14** `needs_judgment` — Please complete this technical assessment before we proceed.
- **#15** `needs_judgment` — Can you send your references and expected start date?
- **#16** `needs_judgment` — Sergio, cuál es tu expectativa salarial y disponibilidad?

## Conclusion

Jev beats the regex baseline by 25% absolute accuracy (100% vs 75%). The baseline short-circuits on courtesy words (`thanks`, `gracias`, `recibido`), so salary asks, interview invites, and bounces that start politely get filed as `simple_ack`. Jev returns a typed choice plus six noul flags; the router only auto-applies `simple_ack` when confidence ≥ 0.80 and no flag is hot. Total model cost on 16 calls: $0.000517.
