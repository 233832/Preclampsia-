def obtener_medicacion_por_riesgo(riesgo: str):
    data = {
        "NINGUNO": {
            "estado": "No indicada",
            "detalle": []
        },

        "MEDIO": {
            "estado": "Control",
            "detalle": [
                {
                    "grupo": "Primera línea",
                    "medicamentos": [
                        {
                            "nombre": "Alfametildopa",
                            "dosis": "250–500 mg VO cada 8 h",
                            "max": "2 g/día"
                        },
                        {
                            "nombre": "Nifedipino LP",
                            "dosis": "20–60 mg VO cada 24 h",
                            "max": "120 mg/día"
                        }
                    ]
                },
                {
                    "grupo": "Alternativos",
                    "medicamentos": [
                        {
                            "nombre": "Labetalol",
                            "dosis": "100–400 mg VO",
                            "max": "1200 mg/día"
                        },
                        {
                            "nombre": "Metoprolol",
                            "dosis": "100–200 mg VO cada 8–12 h",
                            "max": "400 mg/día",
                            "alerta": "Contraindicado en asma"
                        },
                        {
                            "nombre": "Hidralazina",
                            "dosis": "25–50 mg VO cada 6 h",
                            "max": "200 mg/día"
                        }
                    ]
                }
            ]
        },

        "ALTO": {
            "estado": "Indicada",
            "detalle": [
                {
                    "grupo": "Profilaxis",
                    "medicamentos": [
                        {
                            "nombre": "Aspirina",
                            "dosis": "150 mg/día",
                            "inicio": "Antes de semana 16",
                            "horario": "Noche",
                            "suspension": "Semana 34"
                        }
                    ]
                }
            ]
        },

        "HOSPITALIZACION": {
            "estado": "Emergencia",
            "detalle": [
                {
                    "grupo": "Crisis hipertensiva",
                    "medicamentos": [
                        {
                            "nombre": "Nifedipino (rápida)",
                            "dosis": "10 mg VO",
                            "frecuencia": "Cada 10–15 min",
                            "max": "5 dosis"
                        },
                        {
                            "nombre": "Hidralazina IV",
                            "dosis": "5 mg IV",
                            "frecuencia": "Cada 20 min",
                            "max": "5 dosis"
                        }
                    ]
                }
            ]
        }
    }

    return data.get(riesgo, {})