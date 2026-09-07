# Lista de nombres de clientes
nombres_clientes = [
    "  Juan Pérez  ",
    "maría garcía",
    "CARLOS LÓPEZ",
    None,
    "Ana Martínez",
    "juan pérez",
    "",
    "  Pedro Sánchez",
    "MARÍA GARCÍA",  
    "Luis Rodríguez",
    None,
    "Carmen Flores",
    "Laura Ruiz",
    "Miguel Angel",
    "Sofía",
    None,
    "Carlos",
    "  Elena  ",
    "lucia",
    "DIEGO",
    "Ana",
    "Pablo",
    "  ",
    "Fernando",
    "Isabel",
    None,
    "ricardo"
]

# Lista de edades
edades = [
    25, "30", 45, None, "28", 35, -5, 150, "abc", 22, 40, "33",
    29, "40", 55, None, "22", 33, -1, 200, "xyz", 27, 45, "38", 60, "unknown", 19
]

# Lista de correos electrónicos
correos = [
    "juan@email.com",
    "MARIA@EMAIL.COM",
    "correo_invalido",
    None,
    "ana@dominio.com",
    "  pedro@email.com  ",
    "",
    "luis@email",
    "carmen@email.com",
    "usuario@",
    None,
    "contacto@empresa.com",
    "laura@email.com",
    "MIGUEL@EMAIL.COM",
    "sofia_sin_dominio",
    None,
    "carlos@dominio.com",
    "  elena@email.com  ",
    "",
    "lucia@email",
    "diego@email.com",
    "ana@",
    None,
    "pablo@empresa.com",
    "fer@nando.com",
    "isabel@.com",
    "ricardo@mail"
]

# Lista de salarios
salarios = [
    1500.50,
    "2000",
    2500.75,
    None,
    "1800.00",
    3000,
    "abc",
    -500,
    4500.25,
    "3200.50",
    None,
    2800,
    1600.00,
    "2100",
    2600.50,
    None,
    "1900.00",
    3100,
    "def",
    -100,
    4600.00,
    "3300.50",
    None,
    2900,
    5000,
    "free",
    1200
]

# Lista de productos vendidos
productos = [
    "laptop",
    "mouse",
    "TECLADO",
    "laptop",  
    None,
    "  monitor  ",
    "Mouse",  
    "audifonos",
    "",
    "teclado", 
    "webcam",
    None,
    "tablet",
    "monitor",
    "IMPRESORA",
    "tablet",
    None,
    "  teclado  ",
    "Mouse",
    "altavoces",
    "",
    "webcam",
    "microfono",
    "router",
    None,
    "cable hdmi",
    "disco duro"
]

# Lista de cantidades vendidas
cantidades = [
    5, 10, "15", 8, None, "20", 12, "abc", 25, 30, -3, "18",
    6, 11, "16", 9, None, "21", 13, "xyz", 26, 31, -4, "19", 50, "mil", 2
]

# Lista de fechas
fechas = [
    "2024-01-15",
    "15/01/2024",
    "2024-02-20",
    None,
    "20-02-2024",
    "2024/03/10",
    "",
    "invalid_date",
    "2024-04-25",
    None,
    "2024-05-30",
    "30/05/2024",
    "2024-06-15",
    "15/06/2024",
    "2024-07-20",
    None,
    "20-07-2024",
    "2024/08/10",
    "",
    "no_date",
    "2024-09-25",
    None,
    "2024-10-30",
    "30/10/2024",
    "2025-01-01",
    "ayer",
    "2024-12-12"
]

# Lista de códigos postales
codigos_postales = [
    "1101",
    "  1102  ",
    None,
    "1103",
    "ABCD",
    "1101", 
    "",
    "1104",
    "99999",
    "1105",
    None,
    "1102",
    "1106",
    "  1107  ",
    None,
    "1108",
    "EFGH",
    "1106",
    "",
    "1109",
    "00000",
    "1110",
    None,
    "1107",
    "12345",
    "zip",
    "55555"
]

# Lista de calificaciones
calificaciones = [
    85, 92, "88", None, 105, "75", 68, -10, "abc", 95, 78, "82",
    86, 93, "89", None, 110, "76", 69, -20, "def", 96, 79, "83", 100, "A+", 50
]

# Lista de departamentos
departamentos = [
    "Ventas",
    "ventas", 
    "MARKETING",
    "Recursos Humanos",
    None,
    "  IT  ",
    "marketing", 
    "Finanzas",
    "",
    "VENTAS", 
    "IT",
    None,
    "Logistica",
    "logistica",
    "SOPORTE",
    "Administracion",
    None,
    "  Ventas  ",
    "soporte",
    "Direccion",
    "",
    "LOGISTICA",
    "IT",
    None,
    "Compras",
    "Legal",
    "I+D"
]


datos_empresa = {
    'nombres': nombres_clientes,
    'edades': edades,
    'correos': correos,
    'salarios': salarios,
    'productos': productos,
    'cantidades': cantidades,
    'fechas': fechas,
    'codigos_postales': codigos_postales,
    'calificaciones': calificaciones,
    'departamentos': departamentos
}

print("✅ Datos de prueba cargados exitosamente")
print(f"Total de conjuntos de datos: {len(datos_empresa)}")
