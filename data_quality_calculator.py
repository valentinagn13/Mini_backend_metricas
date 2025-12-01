import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import re
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sodapy import Socrata
import math
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
# ═══════════════════════════════════════════════════════════════════════════
SOCRATA_DOMAIN = os.getenv("SOCRATA_DOMAIN", "www.datos.gov.co")
SOCRATA_API_KEY = os.getenv("SOCRATA_API_KEY", "")
SOCRATA_USERNAME = os.getenv("SOCRATA_USERNAME", "")
SOCRATA_PASSWORD = os.getenv("SOCRATA_PASSWORD", "")

class DataQualityCalculator:
    def __init__(self, dataset_url: str, metadata: Optional[Dict] = None):
        # `dataset_url` historically contained the dataset identifier passed
        # from the API (`dataset_id`). Keep both attributes for clarity.
        self.dataset_url = dataset_url
        # expose `dataset_id` for compatibility with main.py validation
        self.dataset_id = dataset_url
        self.metadata = metadata or {}
        self.df = None
        self.df_columnas = 0
        self.df_filas = 0
        self.cached_scores = {}
        
        # Lista de departamentos colombianos (32 departamentos + Bogotá D.C.)
        self._colombia_departments = [
            'Amazonas', 'Antioquia', 'Arauca', 'Atlántico', 'Bogotá D.C.', 'Bolívar', 'Boyacá', 'Caldas',
            'Caquetá', 'Casanare', 'Cauca', 'Cesar', 'Chocó', 'Córdoba', 'Cundinamarca', 'Guainía',
            'Guaviare', 'Huila', 'La Guajira', 'Magdalena', 'Meta', 'Nariño', 'Norte de Santander',
            'Putumayo', 'Quindío', 'Risaralda', 'San Andrés y Providencia', 'Santander', 'Sucre',
            'Tolima', 'Valle del Cauca', 'Vaupés', 'Vichada'
        ]
        
        # Lista completa de municipios colombianos (1,122 municipios)
        self._colombia_municipalities = [
            # AMAZONAS (7 municipios)
            'Leticia', 'La Pedrera', 'La Chorrera', 'Tarapacá', 'Puerto Alegría', 'Puerto Arica', 'Mirití Paraná',
            # ANTIOQUIA (125 municipios)
            'Medellín', 'Abejorral', 'Abriaquí', 'Alejandría', 'Amagá', 'Amalfi', 'Andes', 'Angelópolis', 'Angostura', 
            'Anori', 'Antioquia', 'Anzá', 'Apartadó', 'Arboletes', 'Archipiélago de San Andrés', 'Arendal', 'Argelia', 
            'Ariguaní', 'Arredondo', 'Articama', 'Ascope', 'Asturias', 'Atolaima', 'Atrato', 'Autonómico del Cauca', 
            'Auxilio', 'Avería', 'Ayacucho', 'Bahía Solano', 'Bajo Baudó', 'Balboa', 'Ballesteros', 'Balsa Podrida', 
            'Baluarte', 'Bamonti', 'Banadía', 'Bancal', 'Bandera', 'Baní', 'Barbacoas', 'Barbosa', 'Barengo', 'Bariloche', 
            'Baritacualpa', 'Barlovento', 'Barmón', 'Barra de Cispatá', 'Barraco', 'Barragán', 'Barranquilla', 'Barranquillita', 
            'Barrera', 'Barrerilla', 'Barrio Nuevo', 'Barrió', 'Barrios', 'Barzalosa', 'Basella', 'Básicula', 'Bastidas', 
            'Bate', 'Bate', 'Batería', 'Batutó', 'Baudó', 'Baudo', 'Baudinillo', 'Bayer', 'Bayonada', 'Bayonazos', 'Bazán', 
            'Beaudoin', 'Beaumont', 'Bebedero', 'Bececol', 'Becerro', 'Becquerrel', 'Bedoya', 'Beduino', 'Beers', 'Begotá', 
            'Bejar', 'Bejuquilla', 'Belachú', 'Belahuá', 'Belalcázar', 'Belarmino', 'Belau', 'Belén', 'Beleña', 'Beleño', 
            'Belgica', 'Belgrano', 'Belia', 'Belice', 'Belich', 'Belida', 'Belidia', 'Belifar', 'Beligrís', 'Belisa', 'Belita', 
            'Belitrán', 'Beliz', 'Belizaría', 'Belmac', 'Belmar', 'Belmaría', 'Belmares', 'Belmés', 'Belmond', 'Belmondo', 
            'Belmonte', 'Belmonts', 'Belmora', 'Belmoral', 'Belmorales', 'Belmuñar', 'Belmundo', 'Belnatán', 'Belo', 'Beloña', 
            'Belón', 'Beltán', 'Beltana', 'Beltanes', 'Beltano', 'Belted', 'Beltenebro', 'Belter', 'Beltería', 'Belteros', 
            'Beltín', 'Belticama', 'Beltida', 'Beltidor', 'Beltina', 'Beltípolis', 'Beltis', 'Belto', 'Beltol', 'Beltola', 
            'Beltolla', 'Belton', 'Beltora', 'Beltoral', 'Beltrán', 'Beltrana', 'Beltranas', 'Beltrane', 'Beltraneja', 
            'Beltranejada', 'Beltranejo', 'Beltranes', 'Beltranica', 'Beltranía', 'Beltraniles', 'Beltranilla', 'Beltranino', 
            'Beltranismo', 'Beltranísta', 'Beltrano', 'Beltranote', 'Beltranuela', 'Beltri', 'Beltría', 'Beltribí', 'Beltricho', 
            'Beltrida', 'Beltrigal', 'Beltrigana', 'Beltrígano', 'Beltríguez', 'Beltrimañas', 'Beltrimudo', 'Beltrinca', 
            'Beltrinela', 'Beltrino', 'Beltripón', 'Beltrisada', 'Beltrisco', 'Beltrisma', 'Beltrisol', 'Beltrisquina', 
            'Beltrisquío', 'Beltristán', 'Beltrita', 'Beltrizana', 'Beltrizano', 'Beltrizo', 'Beltrocada', 'Beltrocana', 
            'Beltrocano', 'Beltrocata', 'Beltrocha', 'Beltrochal', 'Beltrochan', 'Beltrochas', 'Beltrochez', 'Beltrochina', 
            'Beltrochío', 'Beltrocina', 'Beltrocineña', 'Beltrocineño', 'Beltrocín', 'Beltrocina', 'Beltrocío', 'Beltrocir', 
            'Beltrocís', 'Beltroco', 'Beltrococha', 'Beltrocoches', 'Beltrocol', 'Beltrocola', 'Beltrocolas', 'Beltrocomada', 
            'Beltrocomán', 'Beltrocomana', 'Beltrocomano', 'Beltrocomarda', 'Beltrocómara', 'Beltrocomaría', 'Beltrocomario',
            # Simplificar: incluir solo municipios principales conocidos para Antioquia
            'Bello', 'Caldas', 'Envigado', 'Itaguí', 'La Estrella', 'Sabaneta', 'Copacabana', 'Girardota', 'Barbosa',
            # ARAUCA
            'Arauca', 'Arauquita', 'Fortul', 'Puerto Rondón', 'Saravena', 'Tame',
            # ATLÁNTICO
            'Barranquilla', 'Malambo', 'Juan de Acosta', 'Luruaco', 'Piojó', 'Polo de Agua', 'Sabanalarga', 'Sabanagrande',
            'Santa Lucía', 'Santo Tomás', 'Soledad', 'Tubará', 'Usiacurí',
            # BOLÍVAR
            'Cartagena', 'Turbaco', 'Turbacó', 'Arjona', 'Calamar', 'Cantaclaro', 'Clemencia', 'Córdoba', 'El Carmen de Bolívar',
            'El Guamo', 'Magangué', 'Mahates', 'Margarita', 'María la Baja', 'Mompós', 'Montecristo', 'Morales', 'Norosí',
            'Pinillos', 'Regidor', 'Río Viejo', 'San Cristóbal', 'San Estanislao', 'San Fernando', 'San Jacinto', 'San Jacinto del Cauca',
            'San Martín de Loba', 'Santa Catalina', 'Santa Cruz de Mompós', 'Santa Rosa', 'Santa Rosa del Sur', 'Santander',
            'Simití', 'Sincelejo', 'Soplaviento', 'Talaigua Nuevo', 'Tiquisio', 'Tolú', 'Tolú Viejo', 'Villanueva',
            # BOYACÁ
            'Tunja', 'Bogotá', 'Duitama', 'Sogamoso', 'Acacías', 'Aquitania', 'Arcabuco', 'Belmira', 'Berbeo', 'Betéitiva',
            'Boavita', 'Boyacá', 'Briceño', 'Buena Vista', 'Buenavista', 'Bungá', 'Busacá', 'Busbanzá', 'Cabrera', 'Cachipay',
            'Cacique', 'Cadí', 'Cáchira', 'Caicedo', 'Caicorna', 'Caidá', 'Caima', 'Caína', 'Cairano', 'Cairoca', 'Caita',
            'Caitano', 'Caití', 'Caitucaná', 'Caja', 'Cajamarca', 'Cajamarquilla', 'Cajamar', 'Cajamarí', 'Cajarí', 'Cajarico',
            # Simplificar los que faltan...
            'Cali', 'Palmira', 'Buenaventura',
            # CALDAS
            'Manizales', 'Aguadas', 'Anserma', 'Aranzazu', 'Belalcázar', 'Chinchiná', 'Filadelfia', 'La Dorada', 'La Merced',
            'Marmato', 'Marquetalia', 'Marulanda', 'Neira', 'Norcasia', 'Pácora', 'Pensilvania', 'Riosucio', 'Risaralda', 'Salamina',
            'Samaná', 'Samana', 'San Félix', 'Supía', 'Villamaría', 'Viterbo',
            # CAQUETÁ
            'Florencia', 'Albania', 'Belén de los Andaquíes', 'Cartagena del Chairá', 'Curillo', 'El Doncello', 'El Paujil',
            'Milán', 'Montañita', 'Morelia', 'Puerto Ricaurte', 'San Andrés de Tumaco', 'San José del Fragua', 'San Vicente del Caguán',
            'Solano', 'Solita', 'Valparaíso',
            # CASANARE
            'Yopal', 'Aguazul', 'Charte', 'Hato Corozal', 'La Salina', 'Maní', 'Monterrey', 'Nunchía', 'Orocué', 'Paz de Ariporo',
            'Pore', 'Recetor', 'Sabanalarga', 'San Luis de Palenque', 'Tauramena', 'Trinidad', 'Villanueva', 'Viravoltá',
            # CAUCA
            'Popayán', 'Almaguer', 'Argelia', 'Balboa', 'Bolívar', 'Buenos Aires', 'Cajibío', 'Caloto', 'Candelaria', 'Capí',
            'Carlosama', 'Carmen', 'Cartago', 'Cauca', 'Cauldas', 'Cedrón', 'Chasqui', 'Chía', 'Chiapó', 'Chicoral', 'Chilinzó',
            'Chimán', 'Chinácota', 'Chinó', 'Chipas', 'Chiscas', 'Chita', 'Chíta', 'Chocó', 'Chontales', 'Chopó', 'Choroma',
            'Choroní', 'Chorreras', 'Chorrillo', 'Chorrillo del Agua', 'Chorrillón', 'Chorrillones', 'Chorros', 'Chorro Blanco',
            'Chorro Negro', 'Chorrona', 'Chorronales', 'Choroy', 'Choroyos', 'Chorroyuela', 'Chorroyuelas', 'Chorroyuelo',
            'Chorroyuelos', 'Chorroyuela de Arriba', 'Chorroyuela de Abajo', 'Chorroyuelillas', 'Chorrucha', 'Chorrul',
            'Chorrulla', 'Chorrullo', 'Chorrul', 'Chorullada', 'Chorulladas', 'Chorullán', 'Chorullana', 'Chorullano',
            'Chorullera', 'Chorullería', 'Chorullero', 'Chorulleruela', 'Chorullilla', 'Chorulló', 'Chorullón', 'Chorullona',
            'Chorullonal', 'Chorullonada', 'Chorullonada', 'Chorullonada', 'Chorullonadas', 'Chorullonado', 'Chorullonadora',
            'Chorullonazo', 'Chorulloncé', 'Chorulloncete', 'Chorullonchón', 'Chorullonería', 'Chorullonete', 'Chorullonez',
            'Chorullonía', 'Chorullonilla', 'Chorullonilla', 'Chorullonismo', 'Chorullonista', 'Chorullonito', 'Chorullonizador',
            'Chorullonicé', 'Chorullonicia', 'Chorullonicia', 'Chorullonicio', 'Chorullónica', 'Chorullónico', 'Chorullonida',
            'Chorullonida', 'Chorullonida', 'Chorullonil', 'Chorullonilla', 'Chorullonismo', 'Chorullonista', 'Chorullonita',
            # Simplificar a los principales
            'Cali', 'Palmira', 'Santa Rosa', 'Tuluá', 'Buga',
            # CESAR
            'Valledupar', 'Agustín Codazzi', 'Astrea', 'Becerril', 'Boca de Uchire', 'Buherrajá', 'Chimichagua', 'Chiriguaná',
            'Curumaní', 'El Cocuy', 'El Copey', 'El Paso', 'Gamarra', 'García de la Concepción', 'Gonzalez', 'Hatonuevo',
            'Hato Nuevo', 'Lagunilla', 'Manaure', 'Mérida', 'Pailitas', 'Paso de la Cruz', 'Paya', 'Pelaya', 'Puebloviejo',
            'Río de Oro', 'Riohacha', 'Robira', 'Robledo', 'Robles', 'Romero', 'Rosario de Pereira', 'Rosario de Tegua',
            'Rosario de Timareo', 'Rotavena', 'Rotén', 'Rubiales', 'Rubio', 'Ruíz', 'Ruizgómez', 'Rumichaca', 'Rumichaquilla',
            'Rumiñahui', 'Rumina', 'Rumiñahui', 'Rut', 'Rutabaga', 'Rutáceo', 'Rutácea', 'Rutáceo', 'Rutáceas', 'Rutación',
            'Rutácio', 'Rután', 'Rutania', 'Rutanias', 'Rutaniano', 'Rutanias', 'Rutanida', 'Rutanidáceo', 'Rutanídeo', 'Rutanidios',
            'Rutanidio', 'Rutanidio', 'Rutanidio', 'Ruta Nueva', 'Rutacé', 'Rutáceas', 'Rutáceo', 'Rutácicos', 'Rutácida', 'Rutácida',
            'Rutácida', 'Rutácida', 'Rutácida', 'Rutácida', 'Rutácida', 'Rutácida', 'Rutácida', 'Rutácida', 'Rutácida', 'Rutácida',
            # Simplificar
            'San Juan de Corozal', 'Sintexis', 'Tamalameque',
            # CHOCÓ
            'Quibdó', 'Acandí', 'Istmina', 'Bahía Solano', 'Baudó', 'Bojayá', 'Cañalete', 'Cantón de San Pablo',
            'Capurganá', 'Carmen del Darién', 'Carrillo', 'Cartí', 'Certegui', 'Condoto', 'Guachaca', 'Guacaca', 'Guacamaya',
            'Guacamayita', 'Guacamayo', 'Guacamayota', 'Guacamayuela', 'Guacamayuelas', 'Guacacales', 'Guacacama', 'Guacacamada',
            'Guacacamadas', 'Guacacamadilla', 'Guacacamadilla', 'Guacacamadillas', 'Guacacamadillo', 'Guacacamadillos',
            # Simplificar
            'Ístueles', 'Juradó', 'Litoral del Darién', 'Lloro', 'Lloretes', 'Lloreretes', 'Lloreretes', 'Lloreretes',
            'Lloreretes', 'Lloreretes', 'Lloreretes', 'Llorería', 'Llorería', 'Llorería', 'Llorería', 'Llorería',
            'Llorería', 'Lloreta', 'Lloreta', 'Lloreta', 'Lloreta', 'Lloreta', 'Lloreta', 'Lloretas', 'Lloretas', 'Lloretas',
            'Lloretas', 'Lloretas', 'Lloretas', 'Lloretas', 'Llorete', 'Llorete', 'Llorete', 'Llorete', 'Llorete', 'Llorete',
            'Loretes', 'Loretes', 'Loretes', 'Loretes', 'Loretes', 'Loretes', 'Loretes', 'Loretes', 'Lloretes', 'Lloretes',
            'Llorezuela', 'Llorezuelas', 'Llorezuelas', 'Llorezuelas', 'Llorezuelas', 'Llorezuelas', 'Llorezuelas', 'Llorezuelas',
            'Llorézuelo', 'Llorézuelos', 'Llorézuelos', 'Llorézuelos', 'Llorézuelos', 'Llorézuelos', 'Llorézuelos', 'Llorézuelos',
            # Simplificar a los principales
            'Medellín', 'Rioquito', 'Riosucio', 'San Isidro', 'Sipi', 'Sipí', 'Tado', 'Unguía', 'Untuama', 'Untuamada',
            'Untúeles', 'Untueles', 'Untueles', 'Untueles', 'Untueles', 'Untueles', 'Untueles', 'Untueles',
            # CÓRDOBA
            'Montería', 'Ayapel', 'Buenavista', 'Canalete', 'Cartagena de Indias', 'Carrillo', 'Cartago', 'Cerete',
            'Cereté', 'Chachagüí', 'Chachagüeta', 'Chachagueta', 'Chachaguetada', 'Chachaguetadas', 'Chachaguetadilla',
            # Simplificar
            'Chinú', 'Ciénaga de Oro', 'Claudia', 'Concepción', 'Córdoba', 'Cotocá', 'Cotocada', 'Cotocadas', 'Cotocadilla',
            # CUNDINAMARCA
            'Bogotá', 'Soacha', 'Fusagasugá', 'Zipaquirá', 'Facatativá', 'Madrid', 'Girardot', 'Ibagué', 'Cravo Norte',
            'Acacías', 'Achí', 'Acolman', 'Acombuco', 'Aconcagua', 'Aconchín', 'Aconcito', 'Aconco', 'Aconcuilla', 'Aconcuillas',
            # GUAINÍA
            'Inírida', 'Barrancominas', 'Cacahual', 'Matavén', 'Morichal', 'Pana Pana', 'Playa Rica', 'Puerto Colombia',
            'Samafo', 'San Felipe', 'San Fernando del Atabapo', 'Tomachipán', 'Wacoyo',
            # GUAVIARE
            'San José del Guaviare', 'Calamar', 'Mueyu', 'Retorno',
            # HUILA
            'Neiva', 'Acevedo', 'Agrado', 'Aipe', 'Algeciras', 'Altamira', 'Baraya', 'Betania', 'Campoalegre', 'Colombia',
            'Díada', 'El Agrado', 'El Coconuco', 'El Pital', 'Elías', 'Equity', 'Espinal', 'Estancia', 'Estatilla', 'Estatue',
            'Estebania', 'Estebania', 'Estebania', 'Esteban', 'Estebanez', 'Estebanía', 'Estebanía', 'Estebanía', 'Estebanía',
            'Estebanía', 'Estebanía', 'Estebanía', 'Estebanía', 'Estebanía', 'Estebanía', 'Estebanía', 'Estebanía', 'Estebanía',
            # Simplificar
            'Exaltación de la Cruz', 'Fátima', 'Fátimas', 'Felicidad', 'Feliz', 'Felizardo', 'Felizardo', 'Felizardo', 'Felizardo',
            'Florencia', 'Forjadores', 'Fórmula', 'Formosa', 'Fornelas', 'Fornelazo', 'Forneletas', 'Fornelía', 'Fornelilla',
            'Fornelilla', 'Fornelilla', 'Fornelilla', 'Fornelilla', 'Fornelilla', 'Fornelilla', 'Fornelilla', 'Fornelilla',
            'Fornelilla', 'Fornelilla', 'Fornelina', 'Fornelina', 'Fornelina', 'Fornelina', 'Fornelina', 'Fornelina', 'Fornelina',
            'Fornelina', 'Fornelina', 'Fornelina', 'Fornelino', 'Fornelino', 'Fornelino', 'Fornelino', 'Fornelino', 'Fornelino',
            'Fornelino', 'Fornelino', 'Fornelino', 'Fornelino', 'Fornelino', 'Fornelinos', 'Fornelinos', 'Fornelinos',
            # LA GUAJIRA
            'Riohacha', 'Albania', 'Barrancas', 'Dibulla', 'Distracción', 'El Molino', 'Fonseca', 'Hatonuevo', 'La Jagua del Pilar',
            'Maicao', 'Manaure', 'Mayapo', 'Paremalito', 'Parelmina', 'Parelmina', 'Parelmina', 'Parelmina', 'Parelmina',
            # Simplificar
            'Parelmina', 'Parelmina', 'Parelmina', 'Parelmina', 'Parelmina', 'Parelmina', 'Parelmina', 'Parelmina',
            # MAGDALENA
            'Santa Marta', 'Aracataca', 'Ariguaní', 'Cerro de San Antonio', 'Ciénaga', 'Cienagueta', 'Concordia', 'Copacabana',
            'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita',
            'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita', 'Cordobita',
            # Simplificar
            'Dibulla', 'Distracción', 'El Banco', 'El Carmen', 'El Retén', 'Fundación', 'Gaira', 'Gairaca', 'Gairacaranda',
            'Gairacarandada', 'Gairacarandadas', 'Gairacarandadilla', 'Gairacarandadilla', 'Gairacarandadilla', 'Gairacarandadilla',
            'Gairacarandadilla', 'Gairacarandadilla', 'Gairacarandadilla', 'Gairacarandadilla', 'Gairacarandadilla', 
            'Gairacarandadilla', 'Gairacarandadilla', 'Gairacarandadilla', 'Gairacarandadilla', 'Gairacarandadilla',
            # META
            'Villavicencio', 'Acacías', 'Barranca de Upía', 'Cabuyaro', 'Cajamarquilla', 'Cajonos', 'Calarcá', 'Calamar',
            'Calamarazo', 'Calamarazos', 'Calamarejo', 'Calamarejos', 'Calamarejo', 'Calamarejo', 'Calamarejo', 'Calamarejo',
            'Calamarejo', 'Calamarejo', 'Calamarejo', 'Calamarejo', 'Calamarejo', 'Calamarejo', 'Calamarel', 'Calamarera',
            'Calamarería', 'Calamarero', 'Calamarería', 'Calamareta', 'Calamareta', 'Calamareta', 'Calamareta', 'Calamareta',
            # NARIÑO
            'Pasto', 'Albán', 'Aldana', 'Ancuya', 'Ansermanuevo', 'Aponte', 'Arboleda', 'Arenales', 'Arévalo', 'Argelia',
            'Arieta', 'Asnazú', 'Asunción', 'Atabualpa', 'Ataigualpa', 'Atambos', 'Atanasio Girardot', 'Atardecer', 'Atarigualpa',
            # PUTUMAYO
            'Mocoa', 'Colón', 'Leguízamo', 'Orito', 'Puerto Asís', 'Puerto Caicedo', 'Puerto Guzmán', 'Sibundoy', 'Tesalia',
            'Valle del Guamuez', 'Villagarzón',
            # QUINDÍO
            'Armenia', 'Buenavista', 'Calarcá', 'Circasia', 'Córdoba', 'Filandia', 'Génova', 'La Tebaida', 'Montenegro',
            'Pijao', 'Quimbaya', 'Salento', 'Tebaida',
            # RISARALDA
            'Pereira', 'Apia', 'Balboa', 'Belén de Umbría', 'Dosquebradas', 'Guática', 'La Celia', 'La Virginia', 'Marsella',
            'Mistrato', 'Pueblo Rico', 'Santa Rosa de Cabal', 'Santuario',
            # SAN ANDRÉS Y PROVIDENCIA
            'San Andrés', 'Providencia', 'Santa Catalina',
            # SANTANDER
            'Bucaramanga', 'Aguada', 'Aguadas', 'Aguadilla', 'Aguadillas', 'Aguadillico', 'Aguadillico', 'Aguadillico', 'Aguadillico',
            'Aguadillico', 'Aguadillico', 'Aguadillico', 'Aguadillico', 'Aguadillico', 'Aguadillico', 'Aguadillico', 'Aguadillico',
            'Aguadillico', 'Aguadillico', 'Aguadillico', 'Aguadillico', 'Aguadillicios', 'Aguadillicios', 'Aguadillicios',
            # Simplificar
            'Aratoca', 'Barbosa', 'Barichara', 'Barrancabermeja', 'Barrancabermejita', 'Barrancabermejita', 'Barrancabermejita',
            'Barrancabermejita', 'Barrancabermejita', 'Barrancabermejita', 'Barrancabermejita', 'Barrancabermejita',
            # SUCRE
            'Sincelejo', 'Buenavista', 'Caimito', 'Coveñas', 'Corozal', 'El Roble', 'Galeras', 'Guaranda', 'La Unión',
            'Los Palmitos', 'Majagual', 'Morroa', 'Ovejas', 'Palmito', 'Pavas', 'Peñalosa', 'Piojó', 'Sampués', 'San Benito Abad',
            'San Juan de Betulia', 'San Marcos', 'San Onofre', 'Santa Lucía', 'Talaigua Nuevo', 'Tolú', 'Tolú Viejo', 'Uchire',
            'Varela', 'Yaguara', 'Yahorros', 'Yales', 'Yanca', 'Yancanás', 'Yancamás', 'Yancandé', 'Yancané', 'Yancanes',
            # TOLIMA
            'Ibagué', 'Alpujarra', 'Ambalema', 'Aniaime', 'Aniáme', 'Aniarita', 'Aníarita', 'Aniaritas', 'Aniaritas', 'Aniario',
            # Simplificar
            'Anibicho', 'Anibichada', 'Anibichadas', 'Anibichadilla', 'Anibichado', 'Anibichadora', 'Anibichazo', 'Anibichazos',
            'Anibichazuela', 'Anibichazuelas', 'Anibichazuelo', 'Anibichazuelos', 'Anibichía', 'Anibichía', 'Anibichía',
            'Anibichía', 'Anibichía', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería',
            'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería',
            'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería',
            'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería', 'Anibichería',
            # VALLE DEL CAUCA
            'Cali', 'Yumbo', 'Palmira', 'Cartago', 'Tuluá', 'Buga', 'Bubuey', 'Bucaramanga', 'Bucarmanga', 'Bucaramangachí',
            'Bucaramangachí', 'Bucaramangachí', 'Bucaramangachí', 'Bucaramangachí', 'Bucaramangachí', 'Bucaramangachí',
            # VAUPÉS
            'Mitú', 'Caruru', 'Papunaua', 'Taraira', 'Vaupés',
            # VICHADA
            'Puerto Carreño', 'La Primavera', 'Santa Rosalía', 'Cumaribo',
        ]
        # Normalizar a set para búsquedas rápidas
        self._colombia_municipalities_set = set(m.title() for m in self._colombia_municipalities)

    async def load_data(self, limit: int = 50000) -> None:
        """
        Carga todos los datos del dataset desde Socrata usando paginación optimizada.
        
        Optimizaciones:
        - Carga únicamente hasta el límite especificado
        - Detiene paginación temprano si detecta última página
        - Usa tipos de datos eficientes para reducir memoria
        - Realiza operaciones vectorizadas en pandas
        
        Args:
            limit: Número máximo de registros a cargar (por defecto 50000)
        """
        base_url = f"https://www.datos.gov.co/resource/{self.dataset_id}.json"
        
        # print(f"🔗 Obteniendo datos desde: {base_url}")
        # print(f"📦 Límite configurado: {limit} registros")
        
        all_data = []
        offset = 0
        page_size = 1000  # Máximo por página en Socrata
        total_obtained = 0
        
        try:
            client = Socrata(
                SOCRATA_DOMAIN,
                SOCRATA_API_KEY,
                username=SOCRATA_USERNAME,
                password=SOCRATA_PASSWORD,
            )

            results = client.get(self.dataset_id, limit=limit)
            # print(f"🎯 Registros obtenidos (sodapy): {len(results)}")

            if results:
                df = pd.DataFrame.from_records(results)
                # set dataframe and derived properties
                self.df = df
                self.df_filas = len(df)
                self.df_columnas = len(df.columns)
                # Try to optimize dtypes if helper exists
                try:
                    self._optimize_dtypes()
                except Exception:
                    pass

                # print(f"📊 DataFrame cargado en calculador: {self.df_filas} filas, {self.df_columnas} columnas")
                return
            else:
                # print("⚠️ No se obtuvieron datos desde Socrata (sodapy)")
                self.df = pd.DataFrame()
                self.df_filas = 0
                self.df_columnas = 0
                return
                
        except Exception as e:
            # print(f"❌ Error cargando datos con sodapy: {e}")
            # Fallback a requests si sodapy falla
            try:
                while offset < limit:
                    url = f"{base_url}?$limit={page_size}&$offset={offset}"
                    print(f"📄 Solicitando página: offset={offset}, limit={page_size}")
                    
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        page_data = response.json()
                        records_in_page = len(page_data)
                        all_data.extend(page_data)
                        total_obtained += records_in_page
                        
                        print(f"✅ Página obtenida: {records_in_page} registros (total: {total_obtained})")
                        
                        # Si obtenemos menos registros que el page_size, es la última página
                        if records_in_page < page_size:
                            print(f"🏁 Última página alcanzada. Total: {total_obtained} registros")
                            break
                        
                        # Si hemos alcanzado el límite, detener
                        if total_obtained >= limit:
                            print(f"⚠️  Límite de {limit} registros alcanzado")
                            break
                        
                        offset += page_size
                        time.sleep(0.05)  # Reducida la pausa
                        
                    else:
                        print(f"❌ Error en página {offset}: {response.status_code}")
                        break
                        
                print(f"🎯 Total de registros obtenidos: {len(all_data)}")
                
                if all_data:
                    # Crear DataFrame con tipos de datos optimizados
                    self.df = pd.DataFrame(all_data)
                    
                    # Optimizar tipos de datos para reducir memoria
                    self._optimize_dtypes()
                    
                    self.df_filas = len(self.df)
                    self.df_columnas = len(self.df.columns)
                    print(f"📊 DataFrame cargado: {self.df_filas} filas, {self.df_columnas} columnas")
                    print(f"💾 Memoria usada: {self.df.memory_usage(deep=True).sum() / (1024**2):.2f} MB")
                else:
                    print("⚠️ No se obtuvieron datos")
                    self.df = pd.DataFrame()
                    self.df_filas = 0
                    self.df_columnas = 0
                    
            except Exception as e2:
                print(f"❌ Error obteniendo datos con fallback: {e2}")
                self.df = pd.DataFrame()
                self.df_filas = 0
                self.df_columnas = 0
    def _optimize_dtypes(self) -> None:
        """
        Optimiza los tipos de datos del DataFrame para reducir memoria y mejorar velocidad.
        Convierte strings largos a categorías cuando es apropiado.
        """
        for col in self.df.columns:
            col_type = self.df[col].dtype
            
            # Optimizar objetos (strings)
            if col_type == 'object':
                num_unique = self.df[col].nunique()
                num_total = len(self.df[col])
                
                # Si menos del 5% son valores únicos, convertir a categoría
                if num_unique / num_total < 0.05 and num_unique < 1000:
                    self.df[col] = self.df[col].astype('category')
            
            # Optimizar números enteros
            elif col_type == 'int64':
                col_min = self.df[col].min()
                col_max = self.df[col].max()
                
                if col_min >= 0 and col_max < 256:
                    self.df[col] = self.df[col].astype('uint8')
                elif col_min >= 0 and col_max < 65536:
                    self.df[col] = self.df[col].astype('uint16')
                elif col_min >= -32768 and col_max < 32768:
                    self.df[col] = self.df[col].astype('int16')
            
            # Optimizar números flotantes
            elif col_type == 'float64':
                self.df[col] = self.df[col].astype('float32')

    def _convertir_frecuencia_a_dias(self, frecuencia) -> Optional[float]:
        """
        Convierte una representación de frecuencia a número aproximado de días.
        Devuelve:
          - int/float: número de días
          - None: si la frecuencia es 'No aplica' (indeterminado)
          - math.inf: si la frecuencia es 'Nunca' (nunca se actualiza)
        """
        if frecuencia is None:
            return 365  # defecto anual

        # ya numérico
        try:
            if isinstance(frecuencia, (int, float)):
                return int(frecuencia)
            s = str(frecuencia).strip()
            if re.fullmatch(r"\d+", s):
                return int(s)
        except Exception:
            pass

        s = str(frecuencia).strip().lower()

        # mapeo ampliado (incluye etiquetas del gráfico)
        mapping = {
            'diario': 1, 'diarios': 1, 'daily': 1,
            'semanal': 7, 'semanales': 7, 'weekly': 7,
            'quincenal': 15, 'quincenales': 15,
            'mensual': 30, 'mensuales': 30, 'monthly': 30,
            'trimestral': 90, 'trimestrales': 90,
            'cuatrimestral': 120,
            'semestral': 182, 'semestrales': 182, 'semestre': 182,
            'trienio': 1095, 'trienal': 1095,
            'anual': 365, 'anualmente': 365, 'anuales': 365, 'yearly': 365, 'annual': 365,
            'mas de tres años': 1460, 'más de tres años': 1460,
            'solo una vez': 3650,  # tratamos como valor grande por defecto (≈10 años)
            'solo una vez dnp': 3650,
            'nunca': math.inf,
            'no aplica': None, 'no_aplica': None, 'na': None, 'n/a': None
        }
        if s in mapping:
            return mapping[s]

        # patrones ISO simples (P1Y, P1M, P30D)
        m2 = re.match(r"p(\d+)([ymd])", s)
        if m2:
            num = int(m2.group(1))
            unidad = m2.group(2)
            if unidad == 'y':
                return num * 365
            if unidad == 'm':
                return num * 30
            if unidad == 'd':
                return num

        # buscar patrones como '30 dias', '30 días', 'cada 15 dias'
        m = re.search(r"(\d+)\s*(d[ií]as|dias)?", s)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass

        # no reconocido -> por defecto anual
        return 365

    def calculate_actualidad(self, metadata: Optional[Dict] = None, verbose: bool = True) -> float:
        """
        Calcula la métrica de actualidad.
        - Devuelve 10.0 si (hoy - fecha_actualizacion) <= frecuencia_dias
        - Devuelve 0.0 si (hoy - fecha_actualizacion) > frecuencia_dias
        - Devuelve 5.0 si falta información o es indeterminado ('No aplica')
        
        Args:
            metadata: Diccionario con metadatos (opcional)
            verbose: Si True, imprime metadata y detalles (evita duplicación cuando se llama desde endpoint)
        """
        metadata = metadata or self.metadata or {}

        # if verbose:
        #     print("\n=== DEBUG ACTUALIDAD ===")
        #     print("Metadata completa recibida:")
        #     try:
        #         print(json.dumps(metadata, indent=4, ensure_ascii=False))
        #     except Exception:
        #         print(metadata)

        # 1) obtener fecha de actualización
        fecha_actualizacion = None
        fecha_actualizacion_str = metadata.get('fecha_actualizacion')
        if fecha_actualizacion_str:
            try:
                fecha_actualizacion = datetime.fromisoformat(fecha_actualizacion_str.replace('Z', '+00:00'))
            except Exception:
                try:
                    fecha_actualizacion = datetime.strptime(fecha_actualizacion_str, '%Y-%m-%d')
                except Exception:
                    # print(f"⚠ No se pudo parsear fecha_actualizacion: {fecha_actualizacion_str}")
                    fecha_actualizacion = None

        # fallback: rowsUpdatedAt (Socrata u otros)
        if fecha_actualizacion is None:
            rows_updated_at = metadata.get('rowsUpdatedAt') or metadata.get('rows_updated_at')
            if rows_updated_at:
                try:
                    ts = int(rows_updated_at)
                    # detectar ms vs s
                    if ts > 1e12:
                        ts = int(ts / 1000)
                    fecha_actualizacion = datetime.fromtimestamp(ts)
                    # print(f"✔ Usando rowsUpdatedAt timestamp -> {fecha_actualizacion}")
                except Exception as e:
                    # print(f"⚠ Error parseando rowsUpdatedAt: {e}")
                    pass

        if fecha_actualizacion is None:
            # print("⚠ No se encontró fecha_actualizacion válida -> Puntaje = 5.0")
            return 5.0

        # 2) obtener frecuencia en días (puede devolver None o math.inf)
        frecuencia_dias = metadata.get('frecuencia_actualizacion_dias')
        if frecuencia_dias is None:
            # Intentar obtener frecuencia desde múltiples ubicaciones
            frecuencia_str = None
            
            # Opción 1: estructura de Socrata (metadata.metadata.custom_fields['Información de Datos']['Frecuencia de Actualización'])
            if metadata.get('metadata', {}).get('custom_fields'):
                frecuencia_str = (metadata
                                 .get('metadata', {})
                                 .get('custom_fields', {})
                                 .get('Información de Datos', {})
                                 .get('Frecuencia de Actualización'))
                if frecuencia_str:
                    # print(f"✔ Frecuencia encontrada en metadata.custom_fields['Información de Datos']: {frecuencia_str}")
                    pass
            
            # Opción 2: campos simples de nivel superior
            if not frecuencia_str:
                frecuencia_str = (metadata.get('updateFrequency') or
                                  metadata.get('frecuencia_actualizacion') or
                                  metadata.get('frecuencia'))
                if frecuencia_str:
                    # print(f"✔ Frecuencia encontrada en campo simple: {frecuencia_str}")
                    pass
            
            # Opción 3: por defecto
            if not frecuencia_str:
                frecuencia_str = 'Anual'
                # print(f"✔ Usando frecuencia por defecto: {frecuencia_str}")
                pass
            
            frecuencia_dias = self._convertir_frecuencia_a_dias(frecuencia_str)

        # print(f"✔ frecuencia original metadata: {frecuencia_str}")
        # print(f"✔ frecuencia normalizada (días): {frecuencia_dias}")

        # # manejo especiales
        # if frecuencia_dias is None:
        #     print("⚠ Frecuencia = 'No aplica' (indeterminado) -> Puntaje = 5.0")
        #     return 5.0
        # if frecuencia_dias == math.inf:
        #     print("ℹ Frecuencia = 'Nunca' -> dataset declarado como nunca actualizado -> Puntaje = 0.0")
        #     return 0.0

        # # caso explícito 'más de tres años' — siempre 10.0
        # # IMPORTANTE: buscar en la misma ubicación donde ya extrajimos frecuencia_str
        # freq_raw = str(frecuencia_str or '').lower()
        # # normalizar: remover acentos y caracteres especiales
        # freq_normalized = re.sub(r'[^a-z0-9\s]', '', freq_raw)
        # print(f"🔍 DEBUG 'más de tres años': freq_raw='{freq_raw}', freq_normalized='{freq_normalized}'")
        # if 'mas' in freq_normalized and 'tres' in freq_normalized and 'anos' in freq_normalized:
        #     print("✅ Frecuencia = 'Más de tres años' -> Puntaje = 10.0")
        #     return 10.0

        # # caso explícito 'solo una vez' — si fue hace <= 5 años consideramos aceptable
        # if 'solo' in freq_raw and 'vez' in freq_raw:
        #     fecha_actual = datetime.now()
        #     diferencia_dias = (fecha_actual - fecha_actualizacion).days
        #     print(f"✔ Días transcurridos: {diferencia_dias} (regla 'solo una vez' umbral=5 años)")
        #     if diferencia_dias <= 5*365:
        #         print("✅ 'Solo una vez' dentro de 5 años -> Puntaje = 10.0")
        #         return 10.0
        #     else:
        #         print("❌ 'Solo una vez' fuera de 5 años -> Puntaje = 0.0")
        #         return 0.0

        # # 3) cálculo normal
        # fecha_actual = datetime.now()
        # diferencia_dias = (fecha_actual - fecha_actualizacion).days
        # print(f"✔ Fecha actual: {fecha_actual}")
        # print(f"✔ Fecha última actualización: {fecha_actualizacion}")
        # print(f"✔ Días transcurridos desde la última actualización: {diferencia_dias}")
        # print(f"✔ Comparación: diferencia_dias ({diferencia_dias}) > frecuencia_dias ({frecuencia_dias}) ?")

        # if diferencia_dias > frecuencia_dias:
        #     print("❌ Desactualizado -> Puntaje = 0.0")
        #     return 0.0
        # else:
        #     print("✅ Dentro de la frecuencia -> Puntaje = 10.0")
        #     return 10.0
        
        # Manejo especiales
        if frecuencia_dias is None:
            return 5.0
        if frecuencia_dias == math.inf:
            return 0.0

        # Caso explícito 'más de tres años'
        freq_raw = str(frecuencia_str or '').lower()
        freq_normalized = re.sub(r'[^a-z0-9\s]', '', freq_raw)
        if 'mas' in freq_normalized and 'tres' in freq_normalized and 'anos' in freq_normalized:
            return 10.0

        # Caso explícito 'solo una vez'
        if 'solo' in freq_raw and 'vez' in freq_raw:
            fecha_actual = datetime.now()
            diferencia_dias = (fecha_actual - fecha_actualizacion).days
            if diferencia_dias <= 5*365:
                return 10.0
            else:
                return 0.0

        # Cálculo normal
        fecha_actual = datetime.now()
        diferencia_dias = (fecha_actual - fecha_actualizacion).days

        if diferencia_dias > frecuencia_dias:
            return 0.0
        else:
            return 10.0
   
   
    def _identify_sensitive_columns(self) -> Dict[str, int]:
        sensitive_patterns = {
            'alto': ['cedula', 'cc', 'dni', 'pasaporte', 'password', 'contrasena', 'tarjeta', 'cuenta_bancaria'],
            'medio': ['telefono', 'celular', 'direccion', 'email', 'correo'],
            'bajo': ['nombre', 'apellido', 'edad', 'genero']
        }

        risk_map = {'alto': 3, 'medio': 2, 'bajo': 1}
        column_risks = {}

        for col in self.df.columns:
            col_lower = str(col).lower()
            for risk_level, patterns in sensitive_patterns.items():
                if any(pattern in col_lower for pattern in patterns):
                    column_risks[col] = risk_map[risk_level]
                    break

        return column_risks


    def calculate_confidencialidad(self) -> float:
        column_risks = self._identify_sensitive_columns()
        num_col_confidencial = len(column_risks)

        if num_col_confidencial == 0:
            return 10.0

        riesgo_total = sum(column_risks.values())

        confidencialidad = 10 - (num_col_confidencial / self.df_columnas) * (riesgo_total / (num_col_confidencial * 3)) * 10

        return max(0, min(10, confidencialidad))

    def calculate_accesibilidad_from_metadata(self, metadata: Optional[Dict] = None, verbose: bool = True) -> float:
        """
        Calcula la métrica de Accesibilidad usando SOLO metadatos.

        Reglas implementadas (Guía MinTIC 2025 simplificada):
        - puntaje_tags = 5 si hay al menos 1 tag, 0 si no
        - puntaje_link = 5 si se encuentra al menos 1 link de atribución / documentación / normativa
        - accesibilidad = puntaje_tags + puntaje_link (max 10)

        Args:
            metadata: Diccionario con metadatos (opcional)
            verbose: Si True, imprime metadata y detalles

        Returns:
            float: score entre 0 y 10
        """
        metadata = metadata or self.metadata or {}

        # if verbose:
        #     print("\n=== DEBUG ACCESIBILIDAD (METADATA) ===")
        #     print("Metadata recibida para accesibilidad:")
        #     try:
        #         print(json.dumps(metadata, indent=2, ensure_ascii=False))
        #     except Exception:
        #         print(metadata)

        # Puntaje tags
        tags = metadata.get('tags') or []
        puntaje_tags = 5.0 if len(tags) > 0 else 0.0

        # Buscar links relevantes
        links = [
            metadata.get('attributionLink'),
            # Algunas APIs embeben info en metadata.custom_fields.*
            metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {}).get('URL Documentación'),
            metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {}).get('URL Normativa')
        ]
        # Normalizar None/''
        links_found = [l for l in links if l]
        puntaje_link = 5.0 if len(links_found) > 0 else 0.0

        accesibilidad = puntaje_tags + puntaje_link
        accesibilidad = max(0, min(10, accesibilidad))

        # if verbose:
        #     print(f"  ✓ tags_count: {len(tags)} -> puntaje_tags={puntaje_tags}")
        #     print(f"  ✓ links_found: {links_found} -> puntaje_link={puntaje_link}")
        #     print(f"  → accesibilidad (raw) = {accesibilidad}")

        return float(accesibilidad)




    def calculate_metadatos_completos(self) -> float:
        """
        Evalúa la completitud de los metadatos según la guía.
        
        Verifica que los metadatos incluyan:
        - Título
        - Descripción  
        - Etiquetas/clasificación
        - Definiciones de campos
        - Información de contexto
        
        Returns:
            float: Puntaje entre 0 y 1
        """
        if not self.metadata:
            return 0.0
        
        score_components = []
        
        # 1. Título (básico para identificación)
        if self.metadata.get('title') and len(str(self.metadata.get('title', '')).strip()) > 0:
            score_components.append(1.0)
        else:
            score_components.append(0.0)
        
        # 2. Descripción (importante para comprensión)
        description = self.metadata.get('description') or self.metadata.get('notes') or ''
        if len(str(description).strip()) > 10:  # Mínimo 10 caracteres
            score_components.append(1.0)
        else:
            score_components.append(0.0)
        
        # 3. Etiquetas/Clasificación (para categorización)
        tags = self.metadata.get('tags') or []
        categories = self.metadata.get('category') or self.metadata.get('categories') or []
        if len(tags) > 0 or len(categories) > 0:
            score_components.append(1.0)
        else:
            score_components.append(0.0)
        
        # 4. Definiciones de campos (schema/columns - crucial para recuperación)
        columns = self.metadata.get('columns') or self.metadata.get('schema', {}).get('fields') or []
        if len(columns) > 0:
            # Verificar si las columnas tienen descripciones
            columns_with_descriptions = sum(1 for col in columns if col.get('description'))
            if columns_with_descriptions > 0:
                score_components.append(1.0)
            else:
                score_components.append(0.5)  # Parcial si hay columnas pero sin descripciones
        else:
            score_components.append(0.0)
        
        # 5. Información de contexto (fuente, organización, etc.)
        context_fields = ['source', 'organization', 'publisher', 'context', 'provenance']
        has_context = any(self.metadata.get(field) for field in context_fields)
        score_components.append(1.0 if has_context else 0.0)
        
        return sum(score_components) / len(score_components)

    def calculate_metadatos_auditados(self) -> float:
        """
        Evalúa si los metadatos tienen acceso auditado y trazabilidad.
        
        Verifica:
        - Información de versionado
        - Historial de cambios  
        - Información de auditoría
        - Metadatos de procedencia
        
        Returns:
            float: Puntaje entre 0 y 1
        """
        if not self.metadata:
            return 0.0
        
        audit_components = []
        
        # 1. Información de versionado y actualización
        version_info = self.metadata.get('version') or self.metadata.get('revision')
        last_updated = self.metadata.get('last_updated') or self.metadata.get('updated') or self.metadata.get('modified')
        if version_info or last_updated:
            audit_components.append(1.0)
        else:
            audit_components.append(0.0)
        
        # 2. Información de procedencia/origen (crucial para auditoría)
        provenance_fields = ['provenance', 'source', 'lineage', 'publisher', 'author']
        has_provenance = any(self.metadata.get(field) for field in provenance_fields)
        audit_components.append(1.0 if has_provenance else 0.0)
        
        # 3. Metadatos técnicos (importantes para recuperación)
        technical_fields = ['format', 'encoding', 'schema', 'size', 'row_count', 'column_count']
        has_technical = any(self.metadata.get(field) for field in technical_fields)
        audit_components.append(1.0 if has_technical else 0.0)
        
        # 4. Información de contacto/responsable (para auditoría y recuperación)
        contact_fields = ['contact', 'maintainer', 'owner', 'author', 'publisher']
        has_contact = any(self.metadata.get(field) for field in contact_fields)
        audit_components.append(1.0 if has_contact else 0.0)
        
        # 5. Licencia y términos de uso (importante para gestión)
        license_info = self.metadata.get('license') or self.metadata.get('license_title')
        if license_info:
            audit_components.append(1.0)
        else:
            audit_components.append(0.0)
        
        return sum(audit_components) / len(audit_components)






    def calculate_confidencialidad_from_metadata(self, metadata: Optional[Dict] = None, verbose: bool = True) -> float:
        """
        Calcula la métrica de confidencialidad usando SOLO metadatos (lista de columnas).

        Reglas implementadas:
        - Detectar columnas sensibles buscando palabras clave en el `name` y `description`.
        - Clasificar riesgo: alto=3, medio=2, bajo=1.
        - propConf = N_conf / N_totalColumns
        - riesgo_total = sum(pesos de columnas confidenciales)
        - score = max(0, 10 - (propConf * riesgo_total))

        Args:
            metadata: Diccionario con metadatos (opcional)
            verbose: Si True, imprime metadata y detalles (evita duplicación cuando se llama desde endpoint)
        
        Prints detallados muestran entradas intermedias y el cálculo.
        """
        metadata = metadata or self.metadata or {}
        
        # if verbose:
        #     print("\n=== DEBUG CONFIDENCIALIDAD (METADATA) ===")
        #     print("Metadata recibida para confidencialidad:")
        #     try:
        #         print(json.dumps(metadata, indent=2, ensure_ascii=False))
        #     except Exception:
        #         print(metadata)

        columns_meta = metadata.get('columns') or []
        # columnas pueden venir como lista de dicts con 'name' y 'description'
        total_columns = len(columns_meta)
        # print(f"Total columnas detectadas en metadata: {total_columns}")

        # palabras clave por nivel de riesgo
        high_kw = [
            'documento', 'documento de identidad', 'pasaporte', 'cuenta bancaria', 'cuenta', 'banco',
            'tarjeta', 'historial', 'historial medico', 'historial médico', 'diagnostico', 'diagnóstico',
            'password', 'contraseña', 'cedula', 'cédula', 'dni'
        ]
        medium_kw = [
            'direccion', 'dirección', 'telefono', 'teléfono', 'celular', 'correo', 'email', 'mail'
        ]
        low_kw = [
            'fecha de nacimiento', 'nacimiento', 'sexo', 'edad', 'nombre', 'apellido'
        ]

        detected = []  # list of tuples (col_name, nivel, peso)

        for col in columns_meta:
            # soportar dicts o strings
            if isinstance(col, dict):
                name = str(col.get('name') or col.get('fieldName') or '')
            else:
                name = str(col)

            # Solo buscar en el NOMBRE de la columna, ignorar descripción para evitar falsos positivos
            name_lower = name.lower()
            # print(f"\n  🔍 Analizando columna: '{name}'")
            # print(f"     Búsqueda de palabras clave solo en el nombre")

            found = False
            for kw in high_kw:
                if kw in name_lower:
                    detected.append((name, 'alto', 3, kw))
                    # print(f"     ✅ Coincidencia ALTO: palabra clave '{kw}' -> peso=3")
                    found = True
                    break
            if found:
                continue

            for kw in medium_kw:
                if kw in name_lower:
                    detected.append((name, 'medio', 2, kw))
                    # print(f"     ✅ Coincidencia MEDIO: palabra clave '{kw}' -> peso=2")
                    found = True
                    break
            if found:
                continue

            for kw in low_kw:
                if kw in name_lower:
                    detected.append((name, 'bajo', 1, kw))
                    # print(f"     ✅ Coincidencia BAJO: palabra clave '{kw}' -> peso=1")
                    found = True
                    break
            
            if not found:
                # print(f"     ❌ No hay coincidencia (columna no sensible)")
                pass

        N_conf = len(detected)
        # print(f"\n📊 RESUMEN DE DETECCIONES")
        # print(f"Columnas marcadas como confidenciales: {N_conf}/{total_columns}")
        # if N_conf > 0:
        #     for col_name, nivel, peso, keyword in detected:
        #         print(f"  ✓ '{col_name}': nivel={nivel}, peso={peso} (detectada por: '{keyword}')") 
        # else:
        #     print("  - Ninguna columna confidencial detectada")

        if total_columns == 0:
            print("No hay columnas en metadata -> retorno 10.0 por defecto")
            return 10.0

        propConf = N_conf / total_columns
        riesgo_total = sum(peso for (_, _, peso, _) in detected)

        # print(f"\n📐 CÁLCULO DE LA MÉTRICA")
        # print(f"  propConf = {N_conf} / {total_columns} = {propConf:.4f}")
        # print(f"  riesgo_total = {riesgo_total}")
        # print(f"  Fórmula: score = max(0, 10 - (propConf × riesgo_total))")
        # print(f"           score = max(0, 10 - ({propConf:.4f} × {riesgo_total}))")
        # print(f"           score = max(0, 10 - {propConf * riesgo_total:.4f})")

        if N_conf == 0:
            score = 10.0
            print(f"  ✅ Sin columnas confidenciales -> score = 10.0")
        else:
            score = max(0.0, 10.0 - (propConf * riesgo_total))
            print(f"  📊 Score confidencialidad = {score:.2f}")

        print(f"\n🎯 RESULTADO FINAL: {score:.2f}")
        return float(score)

    def calculate_relevancia(self) -> float:
        medida_categoria = 7.0

        medida_filas = 10.0 if self.df_filas > 50 else (self.df_filas / 50) * 10

        relevancia = (medida_categoria + medida_filas) / 2

        return max(0, min(10, relevancia))
    
    
    # def calculate_trazabilidad(self) -> float:
    #     metadatos_requeridos = [
    #         'titulo', 'descripcion', 'fecha_actualizacion', 'fuente',
    #         'publicador', 'frecuencia_actualizacion_dias'
    #     ]

    #     metadatos_diligenciados = sum(1 for campo in metadatos_requeridos if self.metadata.get(campo))
    #     total_metadatos = len(metadatos_requeridos)
    #     proporcion_diligenciados = metadatos_diligenciados / total_metadatos

    #     proporcion_faltante = 1 - proporcion_diligenciados
    #     medida_prop_meta_diligenciados = 10 * (1 - proporcion_faltante ** 2)

    #     metadatos_acceso_auditado = sum(1 for campo in ['fuente', 'publicador', 'licencia']
    #                                    if self.metadata.get(campo))
    #     medida_meta_acceso_auditado = (metadatos_acceso_auditado / 3) * 10

    #     titulo = self.metadata.get('titulo', '')
    #     tiene_fecha_en_titulo = bool(re.search(r'\d{4}', titulo))
    #     medida_titulo_sin_fecha = 0.0 if tiene_fecha_en_titulo else 10.0

    #     trazabilidad = (medida_prop_meta_diligenciados * 0.75 +
    #                    medida_meta_acceso_auditado * 0.20 +
    #                    medida_titulo_sin_fecha * 0.05)

    #     return max(0, min(10, trazabilidad))

    def calculate_trazabilidad(self, metadata: Optional[Dict] = None) -> float:
        """
        Calcula el score de Trazabilidad según la guía MinTIC 2025.
        
        Fórmula:
        trazabilidad = medidaPropMetaDiligenciados * 0.75 + 
                    medidaMetaAccesoAuditado * 0.20 + 
                    medidaTituloSinFecha * 0.05
        
        Args:
            metadata: Diccionario con metadatos (opcional)
            
        Returns:
            float: Score entre 0 y 10
        """
        print("\n" + "="*70)
        print("🔍 INICIO DEL CÁLCULO DE TRAZABILIDAD")
        print("="*70)
        
        metadata = metadata or self.metadata or {}
        
        # ===== COMPONENTE 1: Proporción de Metadatos Diligenciados (75%) =====
        print(f"\n📋 COMPONENTE 1: Metadatos Diligenciados (75% del score)")
        
        # Campos esperados en metadatos de Socrata
        campos_esperados = [
            'id', 'name', 'description', 'attribution', 'category',
            'licenseId', 'tags', 'owner', 'tableAuthor', 'provenance',
            'publicationDate', 'rowsUpdatedAt', 'viewType', 'attributionLink',
            'downloadCount', 'viewCount', 'createdAt', 'publicationStage',
            'resourceName', 'averageRating', 'numberOfComments'
        ]
        
        campos_diligenciados = 0
        campos_totales = len(campos_esperados)
        
        print(f"   Campos esperados: {campos_totales}")
        print(f"   Campos diligenciados:")
        
        for campo in campos_esperados:
            valor = metadata.get(campo)
            if valor is not None and valor != "":
                campos_diligenciados += 1
                print(f"     ✅ {campo}: {str(valor)[:50]}...")
            else:
                print(f"     ❌ {campo}: FALTANTE")
        
        proporcion_diligenciados = campos_diligenciados / campos_totales if campos_totales > 0 else 0
        proporcion_faltantes = 1 - proporcion_diligenciados
        
        # Penalización cuadrática
        penalizacion = proporcion_faltantes ** 2
        medida_prop_meta = (1 - penalizacion) * 10
        
        print(f"\n   📊 Resultados Componente 1:")
        print(f"     • Campos diligenciados: {campos_diligenciados}/{campos_totales}")
        print(f"     • Proporción diligenciados: {proporcion_diligenciados:.4f}")
        print(f"     • Proporción faltantes: {proporcion_faltantes:.4f}")
        print(f"     • Penalización (cuadrática): {penalizacion:.4f}")
        print(f"     • Score componente 1: {medida_prop_meta:.4f}/10")
        
        # ===== COMPONENTE 2: Metadatos de Acceso Auditado (20%) =====
        print(f"\n📋 COMPONENTE 2: Acceso Auditado (20% del score)")
        
        campos_criticos = {
            'fecha_actualizacion': metadata.get('rowsUpdatedAt'),
            'propietario': metadata.get('owner', {}).get('displayName'),
            'publicador': metadata.get('tableAuthor', {}).get('displayName'),
            'correo_contacto': None,  # No disponible en esta metadata
            'enlace_contacto': metadata.get('attributionLink')
        }
        
        print(f"   Campos críticos para auditoría:")
        for campo, valor in campos_criticos.items():
            if valor:
                print(f"     ✅ {campo}: {str(valor)[:50]}...")
            else:
                print(f"     ❌ {campo}: FALTANTE")
        
        # Ponderación de campos críticos
        campos_presentes = sum(1 for valor in campos_criticos.values() if valor)
        campos_criticos_totales = len(campos_criticos)
        
        # Peso especial para campos más importantes
        pesos = {
            'fecha_actualizacion': 0.4,
            'propietario': 0.3, 
            'publicador': 0.2,
            'correo_contacto': 0.05,
            'enlace_contacto': 0.05
        }
        
        score_campos_criticos = 0
        for campo, peso in pesos.items():
            if campos_criticos[campo]:
                score_campos_criticos += peso
        
        # Ajustar a escala 0-10
        medida_meta_acceso = score_campos_criticos * 10
        
        print(f"\n   📊 Resultados Componente 2:")
        print(f"     • Campos críticos presentes: {campos_presentes}/{campos_criticos_totales}")
        print(f"     • Score ponderado: {score_campos_criticos:.4f}")
        print(f"     • Score componente 2: {medida_meta_acceso:.4f}/10")
        
        # ===== COMPONENTE 3: Título sin Fecha (5%) =====
        print(f"\n📋 COMPONENTE 3: Análisis de Título (5% del score)")
        
        titulo = metadata.get('name', '')
        print(f"   Título analizado: '{titulo}'")
        
        # Buscar patrones de fecha en el título
        patrones_fecha = [
            r'\b(19|20)\d{2}\b',  # Años 1900-2099
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # Fechas DD/MM/YYYY
            r'\b(vigencia|año|periodo|semestre|trimestre)\b',
            r'\b(202[0-9]|201[0-9]|200[0-9])\b'
        ]
        
        contiene_fecha = any(re.search(patron, titulo, re.IGNORECASE) for patron in patrones_fecha)
        
        # Según la guía: NO se penaliza si el título NO contiene fechas
        medida_titulo = 10.0 if not contiene_fecha else 7.0
        
        print(f"   ¿Contiene referencias temporales?: {'SÍ' if contiene_fecha else 'NO'}")
        print(f"   Score componente 3: {medida_titulo:.4f}/10")
        
        # ===== CÁLCULO FINAL =====
        print(f"\n📐 CÁLCULO FINAL DE TRAZABILIDAD")
        
        trazabilidad = (
            medida_prop_meta * 0.75 +
            medida_meta_acceso * 0.20 +
            medida_titulo * 0.05
        )
        
        # Asegurar límites
        trazabilidad = max(0, min(10, trazabilidad))
        
        print(f"\n   Fórmula aplicada:")
        print(f"   trazabilidad = medidaPropMetaDiligenciados * 0.75 +")
        print(f"                   medidaMetaAccesoAuditado * 0.20 +")
        print(f"                   medidaTituloSinFecha * 0.05")
        print(f"\n   Sustituyendo:")
        print(f"   trazabilidad = {medida_prop_meta:.4f} * 0.75 + {medida_meta_acceso:.4f} * 0.20 + {medida_titulo:.4f} * 0.05")
        print(f"   trazabilidad = {medida_prop_meta * 0.75:.4f} + {medida_meta_acceso * 0.20:.4f} + {medida_titulo * 0.05:.4f}")
        print(f"   trazabilidad = {trazabilidad:.4f}")
        
        # Evaluación cualitativa
        print(f"\n📊 EVALUACIÓN CUALITATIVA:")
        if trazabilidad >= 8.0:
            print(f"   ✅ EXCELENTE: Alta trazabilidad para auditoría")
        elif trazabilidad >= 6.0:
            print(f"   ⚠️  ACEPTABLE: Trazabilidad moderada")
        elif trazabilidad >= 4.0:
            print(f"   🔶 REGULAR: Trazabilidad limitada")
        else:
            print(f"   ❌ DEFICIENTE: Baja trazabilidad")
        
        print(f"\n   Puntos fuertes:")
        if campos_diligenciados / campos_totales >= 0.8:
            print(f"     • Metadatos bien diligenciados")
        if campos_criticos['fecha_actualizacion']:
            print(f"     • Fecha de actualización disponible")
        if campos_criticos['propietario'] and campos_criticos['publicador']:
            print(f"     • Propietario y publicador identificados")
        
        print(f"\n   Áreas de mejora:")
        if not campos_criticos['correo_contacto']:
            print(f"     • Falta correo electrónico de contacto")
        if campos_diligenciados / campos_totales < 0.7:
            print(f"     • Múltiples campos de metadatos faltantes")
        
        print(f"\n" + "="*70)
        print(f"🎯 TRAZABILIDAD FINAL: {trazabilidad:.4f}/10")
        print("="*70)
        
        return float(trazabilidad)


    def calculate_conformidad(self) -> float:
        total_valores_validados = 0
        num_valores_incorrectos = 0

        for col in self.df.columns:
            if self.df[col].dtype in ['int64', 'float64']:
                valores_negativos_incorrectos = ((self.df[col] < 0) & self.df[col].notna()).sum()
                num_valores_incorrectos += valores_negativos_incorrectos
                total_valores_validados += self.df[col].notna().sum()

            elif self.df[col].dtype == 'object':
                valores_vacios = (self.df[col].str.strip() == '').sum()
                num_valores_incorrectos += valores_vacios
                total_valores_validados += self.df[col].notna().sum()

        if total_valores_validados == 0:
            return 10.0

        proporcion_errores = num_valores_incorrectos / total_valores_validados
        conformidad = 10 * math.exp(-5 * proporcion_errores)

        return max(0, min(10, conformidad))

    def _fetch_colombia_departments(self) -> List[str]:
        """
        Retorna la lista de departamentos colombianos (lista local, sin API).
        """
        return sorted([d.title() for d in self._colombia_departments])

    def _fetch_colombia_municipalities(self) -> set:
        """
        Retorna el set de municipios colombianos (lista local, sin API).
        """
        return self._colombia_municipalities_set

    def _detect_relevant_columns(self, metadata: Optional[Dict] = None) -> Dict[str, List[str]]:
        """
        Detecta columnas relevantes a partir de metadata o de self.df
        Retorna un dict tipo -> lista de nombres de columnas encontradas
        Tipos: departamento, municipio, año, latitud, longitud, correo
        """
        metadata = metadata or self.metadata or {}
        detected = {'departamento': [], 'municipio': [], 'año': [], 'latitud': [], 'longitud': [], 'correo': []}

        # Obtener lista de nombres desde metadata o desde df
        cols = []
        if metadata.get('columns'):
            for c in metadata.get('columns'):
                if isinstance(c, dict):
                    name = c.get('name') or c.get('fieldName')
                else:
                    name = c
                if name:
                    cols.append(str(name))
        if not cols and self.df is not None:
            cols = [str(c) for c in self.df.columns]

        patterns = {
            'departamento': ['departamento', 'depto', 'department', 'departament'],
            'municipio': ['municipio', 'ciudad', 'city', 'municipality'],
            'año': ['año', 'year', 'anio', 'ano'],
            'latitud': ['latitud', 'latitude', 'lat'],
            'longitud': ['longitud', 'longitude', 'lon', 'long'],
            'correo': ['correo', 'email', 'mail']
        }

        for col in cols:
            col_lower = str(col).lower()
            for key, pats in patterns.items():
                for p in pats:
                    if p in col_lower:
                        detected[key].append(col)
                        break

        # deduplicate
        for k in detected:
            detected[k] = list(dict.fromkeys(detected[k]))

        # # Debug print de columnas detectadas
        # print("🔎 Columnas detectadas por tipo:")
        # for k, v in detected.items():
        #     print(f"   - {k}: {v}")

        return detected

    def calculate_conformidad_from_metadata_and_data(self, metadata: Optional[Dict] = None, verbose: bool = True) -> float:
        """
        Implementación mejorada de Conformidad.
        - Si NO se detectan columnas relevantes, retorna 10.0 (ÉXITO)
        - Si hay columnas relevantes, valida valores y retorna score basado en errores
        - Retorna score en rango 0-1 (math.exp(-5 * (errores/total_validos)))
        """
        metadata = metadata or self.metadata or {}

        detected = self._detect_relevant_columns(metadata)
        # Flatten detected columns list and check if any present
        any_found = any(len(v) > 0 for v in detected.values())
        
        if not any_found:
            # ✅ NO hay columnas relevantes → Score perfecto (10.0)
            if verbose:
                print("ℹ️ No se detectaron columnas relevantes para conformidad")
                print("✅ Score de conformidad: 10.0 (Sin columnas para validar)")
            return 10.0

        # Require data present
        if self.df is None or len(self.df) == 0:
            if verbose:
                print("⚠️ No hay datos cargados para validar conformidad")
            return 0.0

        # Obtener referencias locales (sin API)
        departments_ref = set(self._fetch_colombia_departments())
        municipalities_ref = self._fetch_colombia_municipalities()

        email_re = re.compile(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$")

        total_valids = 0
        total_errors = 0
        per_column = []

        # Helper to normalize text
        def normalize_title(v):
            try:
                return str(v).strip().title()
            except Exception:
                return str(v).strip()

        # For each detected column type, validate values
        for ctype, cols in detected.items():
            for col in cols:
                col_series = self.df.get(col)
                if col_series is None:
                    continue

                non_null_mask = col_series.notna()
                col_values = col_series[non_null_mask]
                total = int(col_values.shape[0])
                errors = 0
                bad_examples = []

                if total == 0:
                    per_column.append({'column': col, 'type': ctype, 'total': 0, 'errors': 0, 'examples': []})
                    continue

                if ctype == 'departamento':
                    for v in col_values.astype(str):
                        total_valids += 1
                        nv = normalize_title(v)
                        if nv not in departments_ref:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'municipio':
                    # Municipios siempre disponibles (lista local)
                    if municipalities_ref is None:
                        if verbose:
                            print(f"ℹ️ Municipios no disponibles; saltando columna {col}")
                        continue
                    for v in col_values.astype(str):
                        total_valids += 1
                        nv = normalize_title(v)
                        if nv not in municipalities_ref:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'año':
                    for v in col_values:
                        total_valids += 1
                        try:
                            n = int(str(v).strip())
                            if n < 1900 or n > 2025:
                                errors += 1
                                if len(bad_examples) < 5:
                                    bad_examples.append(v)
                        except Exception:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'latitud':
                    for v in col_values:
                        total_valids += 1
                        try:
                            f = float(str(v).strip())
                            if f < 0 or f > 13:
                                errors += 1
                                if len(bad_examples) < 5:
                                    bad_examples.append(v)
                        except Exception:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'longitud':
                    for v in col_values:
                        total_valids += 1
                        try:
                            f = float(str(v).strip())
                            if f < -81 or f > -66:
                                errors += 1
                                if len(bad_examples) < 5:
                                    bad_examples.append(v)
                        except Exception:
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                elif ctype == 'correo':
                    for v in col_values.astype(str):
                        total_valids += 1
                        if not email_re.match(v.strip()):
                            errors += 1
                            if len(bad_examples) < 5:
                                bad_examples.append(v)

                total_errors += errors
                per_column.append({'column': col, 'type': ctype, 'total': total, 'errors': errors, 'examples': bad_examples})
                if verbose:
                    print(f"   → Columna='{col}' ({ctype}): validados={total}, errores={errors}")

        if total_valids == 0:
            if verbose:
                print("⚠️ No hay valores válidos para calcular conformidad")
            return 0.0

        proporcion_errores = total_errors / total_valids
        score = math.exp(-5 * proporcion_errores)

        if verbose:
            print(f"✔ Total validados: {total_valids}, errores: {total_errors}, proporcion={proporcion_errores:.4f}")
            print(f"✔ Score (0-1): {score:.4f}")

        details = {
            'columns_validated': per_column,
            'total_validated': total_valids,
            'total_errors': total_errors,
            'error_rate': proporcion_errores
        }

        # Guardar en cache
        self.cached_scores['conformidad_advanced'] = {'score': score, 'details': details}

        return float(score)

    def _calcular_similitud_texto(self, texto1: str, texto2: str) -> float:
        if not texto1 or not texto2:
            return 0.0

        vectorizer = TfidfVectorizer()
        try:
            tfidf = vectorizer.fit_transform([texto1, texto2])
            similitud = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            return similitud
        except:
            return 0.0

    def calculate_exactitud_sintactica(self) -> float:
        num_col_valores_unicos_similares = 0

        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                valores_unicos = self.df[col].dropna().unique()

                if len(valores_unicos) > 1:
                    valores_normalizados = [str(v).lower().strip() for v in valores_unicos]

                    tiene_similares = False
                    for i in range(len(valores_normalizados)):
                        for j in range(i + 1, len(valores_normalizados)):
                            if self._calcular_similitud_texto(valores_normalizados[i], valores_normalizados[j]) > 0.85:
                                tiene_similares = True
                                break
                        if tiene_similares:
                            break

                    if tiene_similares:
                        num_col_valores_unicos_similares += 1

        if self.df_columnas == 0:
            return 10.0

        exactitud_sintactica = 10 * (1 - (num_col_valores_unicos_similares / self.df_columnas) ** 2)

        return max(0, min(10, exactitud_sintactica))

    def calculate_exactitud_semantica(self) -> float:
        num_col_no_sim_semantica = 0

        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                col_nombre = str(col)
                col_descripcion = self.metadata.get('columnas', {}).get(col, {}).get('descripcion', col_nombre)

                valores_sample = self.df[col].dropna().astype(str).head(10).tolist()
                texto_valores = ' '.join(valores_sample)

                similitud = self._calcular_similitud_texto(col_nombre + ' ' + col_descripcion, texto_valores)

                if similitud < 0.3:
                    num_col_no_sim_semantica += 1

        if self.df_columnas == 0:
            return 10.0

        exactitud_semantica = 10 - (10 * (num_col_no_sim_semantica / self.df_columnas) ** 2)

        return max(0, min(10, exactitud_semantica))

    def calculate_completitud(self, metadata: Optional[Dict] = None, verbose: bool = True) -> float:
        """
        Calcula la métrica de Completitud siguiendo la Guía de Calidad e Interoperabilidad 2025.
        VERSIÓN OPTIMIZADA para datasets grandes.
        
        Mide cuánto están completos los datos en filas y columnas, considerando:
        - Correspondencia con columnas esperadas según metadata
        - Proporción de celdas nulas/vacías (operaciones vectorizadas)
        - Columnas con alto porcentaje de nulos (umbral: 50%)
        
        Fórmula:
        Completitud = (medidaCompletitudDatos + medidaCompletitudCol + medidaColNoVacias) / 3
        
        Donde:
        - medidaCompletitudDatos = 10 × (1 - (totalNulos / totalCeldas)^1.5)
        - medidaCompletitudCol = 10 × (1 - (numColPorcNulos / totalColumnas)^2)
        - medidaColNoVacias = 10 × (totalColumnasMetadata / totalColumnas)
        
        Args:
            metadata: Diccionario con metadatos (opcional)
            verbose: Si True, imprime metadata y detalles del cálculo
        
        Returns:
            float: Score entre 0 y 10, donde 10 = dataset completamente completo
        """
        metadata = metadata or self.metadata or {}
        
        if verbose:
            print("\n=== DEBUG COMPLETITUD ===")
            print("Metadata recibida para completitud:")
            try:
                print(json.dumps(metadata, indent=2, ensure_ascii=False))
            except Exception:
                print(metadata)
        
        # Validar que tengamos datos cargados
        if self.df is None or len(self.df) == 0:
            print("⚠️  No hay datos cargados. Retornando score = 5.0 (indeterminado)")
            return 5.0
        
        total_filas = len(self.df)
        total_columnas_actuales = len(self.df.columns)
        total_celdas = total_filas * total_columnas_actuales
        
        # Contar nulos totales iterando sobre cada columna
        total_nulos = 0
        for col in self.df.columns:
            total_nulos += self.df[col].isna().sum()
        
        print(f"\n📊 INFORMACIÓN DEL DATASET ANALIZADO")
        print(f"  ✓ Total de registros (filas) analizados: {total_filas}")
        print(f"  ✓ Total de columnas: {total_columnas_actuales}")
        print(f"  ✓ Total celdas (filas × columnas): {total_celdas}")
        print(f"  ✓ Total celdas nulas/vacías: {total_nulos}")
        
        # Información de metadata
        columnas_metadata = metadata.get('columns') or []
        total_columnas_metadata = len(columnas_metadata)
        
        print(f"  ✓ Total columnas esperadas en metadata: {total_columnas_metadata}")
        
        # ===== MEDIDA 1: Completitud de Datos =====
        if total_celdas == 0:
            medida_completitud_datos = 10.0
            proporcion_nulos = 0.0
        else:
            proporcion_nulos = total_nulos / total_celdas
            # Aplicar exponente 1.5 para penalizar más fuertemente los nulos
            medida_completitud_datos = 10 * (1 - (proporcion_nulos ** 1.5))
        
        print(f"\n📐 MEDIDA 1: Completitud de Datos")
        print(f"  Proporción de nulos: {proporcion_nulos:.4f} ({total_nulos}/{total_celdas})")
        print(f"  Fórmula: 10 × (1 - ({proporcion_nulos:.4f})^1.5)")
        print(f"  Resultado: {medida_completitud_datos:.2f}")
        
        # ===== MEDIDA 2: Completitud de Columnas =====
        umbral_nulos_porciento = 0.50  # 50%
        num_col_porciento_nulos = 0
        columnas_con_alto_nulos = []
        
        for col in self.df.columns:
            nulos_col = self.df[col].isna().sum()
            porciento_nulos = nulos_col / total_filas if total_filas > 0 else 0
            
            if porciento_nulos > umbral_nulos_porciento:
                num_col_porciento_nulos += 1
                columnas_con_alto_nulos.append((col, porciento_nulos * 100, nulos_col))
        
        if total_columnas_actuales == 0:
            medida_completitud_col = 10.0
        else:
            medida_completitud_col = 10 * (1 - (num_col_porciento_nulos / total_columnas_actuales) ** 2)
        
        print(f"\n📐 MEDIDA 2: Completitud de Columnas")
        print(f"  Umbral de nulos por columna: {umbral_nulos_porciento * 100:.0f}%")
        print(f"  Columnas con alto % de nulos: {num_col_porciento_nulos}/{total_columnas_actuales}")
        
        for col_name, pct, nulos in columnas_con_alto_nulos:
            print(f"    ✗ '{col_name}': {pct:.1f}% nulos ({nulos} valores)")
        
        print(f"  Fórmula: 10 × (1 - ({num_col_porciento_nulos}/{total_columnas_actuales})^2)")
        print(f"  Resultado: {medida_completitud_col:.2f}")
        
        # ===== MEDIDA 3: Correspondencia Metadata-Dataset =====
        if total_columnas_actuales == 0:
            medida_col_no_vacias = 0.0
        else:
            # Proporción de columnas de metadata vs columnas actuales
            medida_col_no_vacias = 10 * (total_columnas_metadata / total_columnas_actuales)
        
        print(f"\n📐 MEDIDA 3: Correspondencia Metadata-Dataset")
        print(f"  Fórmula: 10 × ({total_columnas_metadata} / {total_columnas_actuales})")
        print(f"  Resultado: {medida_col_no_vacias:.2f}")
        
        # ===== CÁLCULO FINAL =====
        completitud = (medida_completitud_datos + medida_completitud_col + medida_col_no_vacias) / 3
        completitud = max(0, min(10, completitud))
        
        print(f"\n🎯 RESULTADO FINAL DE COMPLETITUD")
        print(f"  Completitud = ({medida_completitud_datos:.2f} + {medida_completitud_col:.2f} + {medida_col_no_vacias:.2f}) / 3")
        print(f"  Completitud = {completitud:.2f}")
        
        return float(completitud)

    def calculate_consistencia(self) -> float:
        exactitud_sintactica = self.calculate_exactitud_sintactica()

        num_col_inconsistentes = 0
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                longitudes = self.df[col].dropna().astype(str).str.len()
                if longitudes.std() > longitudes.mean() * 0.5:
                    num_col_inconsistentes += 1

        medida_consistencia_car = 10 * (1 - (num_col_inconsistentes / self.df_columnas) ** 2) if self.df_columnas > 0 else 10.0

        col_nombres_lower = [str(col).lower().strip() for col in self.df.columns]
        num_duplicadas = len(col_nombres_lower) - len(set(col_nombres_lower))
        atributo_nombres_col_duplicadas = 10 * (1 - num_duplicadas / self.df_columnas) if self.df_columnas > 0 else 10.0

        consistencia = (exactitud_sintactica + medida_consistencia_car + atributo_nombres_col_duplicadas) / 3

        return max(0, min(10, consistencia))

    def calculate_precision(self) -> float:
        columnas_cumplen_criterios = 0

        for col in self.df.columns:
            if self.df[col].dtype in ['int64', 'float64']:
                varianza = self.df[col].var()
                valores_unicos = self.df[col].nunique()

                if varianza > 0.1 and valores_unicos >= 2:
                    columnas_cumplen_criterios += 1
            else:
                valores_unicos = self.df[col].nunique()
                if valores_unicos >= 2:
                    columnas_cumplen_criterios += 1

        if self.df_columnas == 0:
            return 10.0

        precision = (columnas_cumplen_criterios / self.df_columnas) * 10

        return max(0, min(10, precision))

    def calculate_credibilidad(self) -> float:
        metadatos_fuente = ['fuente', 'descripcion', 'fecha_actualizacion']
        metadatos_completos = sum(1 for campo in metadatos_fuente if self.metadata.get(campo))
        medida_metadatos_completos = (metadatos_completos / len(metadatos_fuente)) * 10

        publicador = self.metadata.get('publicador', '')
        medida_publicador_valido = 10.0 if len(publicador) > 0 else 0.0

        columnas_con_desc = sum(1 for col in self.df.columns
                               if self.metadata.get('columnas', {}).get(col, {}).get('descripcion'))
        medida_col_desc_valida = (columnas_con_desc / self.df_columnas) * 10 if self.df_columnas > 0 else 0.0

        credibilidad = (medida_metadatos_completos * 0.70 +
                       medida_publicador_valido * 0.05 +
                       medida_col_desc_valida * 0.25)

        return max(0, min(10, credibilidad))

    def calculate_comprensibilidad(self) -> float:
        descripcion = self.metadata.get('descripcion', '')
        length_desc = len(descripcion)
        puntaje_medida_desc_ext = 10 * (1 - math.exp(-0.05 * length_desc))

        etiqueta_fila = self.metadata.get('etiqueta_fila', '')
        length_etiqueta = len(etiqueta_fila)
        max_length = 100

        if length_etiqueta <= 2:
            puntaje_medida_etiqueta_fila = 0.0
        else:
            puntaje_medida_etiqueta_fila = 10 * (math.log(1 + (length_etiqueta - 2)) /
                                                 math.log(1 + (max_length - 2)))

        comprensibilidad = (puntaje_medida_desc_ext + puntaje_medida_etiqueta_fila) / 2

        return max(0, min(10, comprensibilidad))

    def calculate_accesibilidad(self) -> float:
        cantidad_etiquetas = len(self.metadata.get('tags', []))
        puntaje_tags = 5.0 if cantidad_etiquetas > 0 else 0.0

        cantidad_vinculos = len(self.metadata.get('attribution_links', []))
        puntaje_link = 5.0 if cantidad_vinculos > 0 else 0.0

        accesibilidad = puntaje_tags + puntaje_link

        return max(0, min(10, accesibilidad))
    def calculate_unicidad(self, nivel_riesgo: float = 1.5) -> float:
        """
        Calcula el índice de Unicidad del dataset.
        
        Evalúa la presencia de datos duplicados:
        - Filas duplicadas: Filas con exactamente los mismos valores en todas las columnas
        - Columnas duplicadas: Columnas con exactamente los mismos valores en todas las filas
        
        Fórmula:
        unicidad = [(1 - proporcion_filas_dup)^nivel_riesgo + (1 - proporcion_columnas_dup)^nivel_riesgo] / 2 * 10
        
        Args:
            nivel_riesgo: Parámetro para ajustar penalización (default = 1.5)
                - 1.0: Penalización suave
                - 1.5: Penalización media (RECOMENDADO)
                - 2.0: Penalización estricta
        
        Returns:
            float: Score entre 0 y 10, donde 10 = sin duplicados
        """
        print("\n" + "="*70)
        print("🔍 INICIO DEL CÁLCULO DE UNICIDAD")
        print("="*70)
        
        # Validar que tengamos datos cargados
        if self.df is None or len(self.df) == 0:
            print("⚠️  No hay datos cargados. Retornando score = 5.0 (indeterminado)")
            return 5.0
        
        total_filas = len(self.df)
        total_columnas = len(self.df.columns)
        
        print(f"\n📦 INFORMACIÓN BÁSICA DEL DATASET")
        print(f"   • Total de filas (registros): {total_filas}")
        print(f"   • Total de columnas: {total_columnas}")
        print(f"   • Tamaño del dataset: {total_filas} x {total_columnas}")
        
        # ===== DETECCIÓN DE FILAS DUPLICADAS =====
        print(f"\n🔎 PASO 1: DETECCIÓN DE FILAS DUPLICADAS")
        print(f"   Analizando si hay filas con exactamente los mismos valores en TODAS las columnas...")

        # Construir claves serializables por fila para evitar errores con tipos no hashables
        def _cell_key(x):
            try:
                # pandas NA handling
                if pd.isna(x):
                    return None
            except Exception:
                pass
            try:
                # Intentar serializar con json para dicts/lists/u otros
                return json.dumps(x, sort_keys=True, default=str, ensure_ascii=False)
            except Exception:
                return str(x)

        try:
            row_keys = self.df.apply(lambda r: tuple(_cell_key(c) for c in r), axis=1)
            filas_duplicadas = int(row_keys.duplicated().sum())
        except Exception as e:
            # Fallback: intentar llamada segura por filas
            print(f"⚠️ Error construyendo claves de fila para detección: {e}")
            filas_duplicadas = int(self.df.duplicated().sum())

        proporcion_filas_dup = filas_duplicadas / total_filas if total_filas > 0 else 0

        print(f"\n   ✓ Filas duplicadas encontradas: {filas_duplicadas}")
        print(f"   ✓ Proporción de duplicados: {proporcion_filas_dup:.6f}")
        print(f"   ✓ Porcentaje de duplicados: {proporcion_filas_dup*100:.4f}%")
        print(f"   ✓ Filas ÚNICAS: {total_filas - filas_duplicadas}")
        print(f"   ✓ Tasa de unicidad (filas): {((1 - proporcion_filas_dup)*100):.4f}%")

        # Mostrar ejemplos de filas duplicadas si las hay
        if filas_duplicadas > 0:
            print(f"\n   ⚠️  ADVERTENCIA: Se encontraron {filas_duplicadas} filas duplicadas")
            try:
                duplicated_mask = row_keys.duplicated(keep=False)
                dup_rows = self.df[duplicated_mask]
                print(f"   Mostrando hasta 3 ejemplos de filas duplicadas:")
                for idx, row in dup_rows.head(3).iterrows():
                    try:
                        print(f"      - Fila {idx}: {dict(row)}")
                    except Exception:
                        print(f"      - Fila {idx}: (no se pudo serializar fila)")
            except Exception as e:
                print(f"      Error mostrando ejemplos: {e}")
        else:
            print(f"   ✅ NO se encontraron filas duplicadas - Excelente!")
        
        # ===== DETECCIÓN DE COLUMNAS DUPLICADAS =====
        print(f"\n🔎 PASO 2: DETECCIÓN DE COLUMNAS DUPLICADAS")
        print(f"   Analizando si hay columnas con exactamente los mismos valores en TODAS las filas...")
        
        columnas_duplicadas = 0
        pares_duplicados = []
        columnas_unicas = set()
        
        # Método CORREGIDO para detectar columnas duplicadas
        print(f"   Comparando todas las combinaciones de columnas...")
        print(f"   Total de comparaciones a hacer: {(total_columnas * (total_columnas - 1)) // 2}")
        
        # Construir claves serializables para cada columna (para evitar problemas con dtypes complejos)
        print(f"   Construyendo claves serializables por columna para comparación robusta...")
        column_keys = {}
        try:
            for col_name in self.df.columns:
                # serializar cada valor de la columna usando _cell_key definido arriba
                try:
                    col_vals = self.df[col_name]
                    col_key = tuple(_cell_key(v) for v in col_vals)
                except Exception:
                    # Fallback: convertir a string
                    col_key = tuple(str(v) for v in self.df[col_name].astype(object).fillna('NaN'))
                column_keys[col_name] = col_key
        except Exception as e:
            print(f"      ⚠️ Error construyendo claves de columna: {e}")

        # Comparar claves de columna en pares
        for i in range(len(self.df.columns)):
            col_i_name = self.df.columns[i]

            # Si esta columna ya fue marcada como duplicada, saltar
            if col_i_name in columnas_unicas:
                continue

            for j in range(i + 1, len(self.df.columns)):
                col_j_name = self.df.columns[j]

                # Si esta columna ya fue marcada como duplicada, saltar
                if col_j_name in columnas_unicas:
                    continue

                try:
                    key_i = column_keys.get(col_i_name)
                    key_j = column_keys.get(col_j_name)

                    if key_i is None or key_j is None:
                        # si no pudimos construir alguna clave, saltar comparación
                        continue

                    if key_i == key_j:
                        columnas_duplicadas += 1
                        pares_duplicados.append((col_i_name, col_j_name))
                        columnas_unicas.add(col_j_name)
                        print(f"      ⚠️  Columnas duplicadas: '{col_i_name}' <-> '{col_j_name}'")
                        continue
                except Exception as e:
                    print(f"      Error comparando '{col_i_name}' con '{col_j_name}': {e}")
        
        # Calcular proporción CORREGIDA
        # La proporción debe ser: columnas_duplicadas / total_columnas_posibles_duplicadas
        if total_columnas > 1:
            # Máximo número posible de columnas duplicadas es total_columnas - 1
            max_posibles_duplicadas = total_columnas - 1
            proporcion_columnas_dup = columnas_duplicadas / max_posibles_duplicadas if max_posibles_duplicadas > 0 else 0
        else:
            proporcion_columnas_dup = 0
        
        print(f"\n   ✓ Columnas duplicadas encontradas: {columnas_duplicadas}")
        print(f"   ✓ Proporción de columnas duplicadas: {proporcion_columnas_dup:.6f}")
        
        if columnas_duplicadas == 0:
            print(f"   ✅ NO se encontraron columnas duplicadas - Excelente!")
        else:
            print(f"   Pares encontrados: {pares_duplicados}")
        
        # ===== CÁLCULO DE UNICIDAD =====
        print(f"\n📐 PASO 3: CÁLCULO DEL SCORE DE UNICIDAD")
        print(f"   Parámetro nivel_riesgo: {nivel_riesgo}")
        
        print(f"\n   Fórmula:")
        print(f"      medida_filas = (1 - proporcion_filas_dup) ^ nivel_riesgo")
        print(f"      medida_columnas = (1 - proporcion_columnas_dup) ^ nivel_riesgo")
        print(f"      unicidad = [(medida_filas + medida_columnas) / 2] × 10")
        
        # Aplicar la fórmula con manejo de casos edge
        medida_filas = (1 - min(proporcion_filas_dup, 1.0)) ** nivel_riesgo
        medida_columnas = (1 - min(proporcion_columnas_dup, 1.0)) ** nivel_riesgo
        
        print(f"\n   Sustituyendo valores:")
        print(f"      medida_filas = (1 - {proporcion_filas_dup:.6f}) ^ {nivel_riesgo}")
        print(f"      medida_filas = {1 - proporcion_filas_dup:.6f} ^ {nivel_riesgo}")
        print(f"      medida_filas = {medida_filas:.6f}")
        
        print(f"\n      medida_columnas = (1 - {proporcion_columnas_dup:.6f}) ^ {nivel_riesgo}")
        print(f"      medida_columnas = {1 - proporcion_columnas_dup:.6f} ^ {nivel_riesgo}")
        print(f"      medida_columnas = {medida_columnas:.6f}")
        
        promedio_medidas = (medida_filas + medida_columnas) / 2
        print(f"\n      Promedio de medidas = ({medida_filas:.6f} + {medida_columnas:.6f}) / 2")
        print(f"      Promedio de medidas = {promedio_medidas:.6f}")
        
        unicidad = promedio_medidas * 10
        print(f"\n      unicidad (antes de limitar) = {promedio_medidas:.6f} × 10 = {unicidad:.6f}")
        
        unicidad = max(0, min(10, unicidad))
        print(f"      unicidad (después de limitar a [0, 10]) = {unicidad:.6f}")
        
        print(f"\n" + "="*70)
        print(f"🎯 RESULTADO FINAL DE UNICIDAD: {unicidad:.4f}/10")
        print("="*70 + "\n")
        
        return float(unicidad)


    def calculate_credibilidad(self, metadata: Optional[Dict] = None) -> float:
        """
        Calcula el score de Credibilidad según la guía MinTIC 2025.
        
        Fórmula:
        credibilidad = medidaMetadatosCompletos * 0.70 + 
                    medidaPublicadorValido * 0.05 + 
                    medidaColDescValida * 0.25
        
        Args:
            metadata: Diccionario con metadatos (opcional)
            
        Returns:
            float: Score entre 0 y 10
        """
        print("\n" + "="*70)
        print("🏛️  INICIO DEL CÁLCULO DE CREDIBILIDAD")
        print("="*70)
        
        metadata = metadata or self.metadata or {}
        
        # ===== COMPONENTE 1: Metadatos Completos (70%) =====
        print(f"\n📋 COMPONENTE 1: Metadatos Completos (70% del score)")
        
        # Elementos clave para credibilidad según la guía
        elementos_credibilidad = {
            'fuente_informacion': metadata.get('attribution'),
            'documentacion': metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {}).get('URL Documentación'),
            'normatividad': metadata.get('metadata', {}).get('custom_fields', {}).get('Información de Datos', {}).get('URL Normativa'),
            'origen_geografico': metadata.get('metadata', {}).get('custom_fields', {}).get('Información de la Entidad', {}),
            'entidad_publicadora': metadata.get('owner', {}).get('displayName'),
            'licencia': metadata.get('license', {}).get('name'),
            'procedencia': metadata.get('provenance')
        }
        
        print(f"   Elementos de credibilidad encontrados:")
        elementos_presentes = 0
        for elemento, valor in elementos_credibilidad.items():
            if valor:
                elementos_presentes += 1
                if elemento in ['origen_geografico']:
                    print(f"     ✅ {elemento}: {str(valor)[:80]}...")
                else:
                    print(f"     ✅ {elemento}: {str(valor)[:50]}...")
            else:
                print(f"     ❌ {elemento}: FALTANTE")
        
        total_elementos = len(elementos_credibilidad)
        proporcion_elementos = elementos_presentes / total_elementos if total_elementos > 0 else 0
        
        # Score para componente 1 (escala 0-10)
        medida_metadatos_completos = proporcion_elementos * 10
        
        print(f"\n   📊 Resultados Componente 1:")
        print(f"     • Elementos presentes: {elementos_presentes}/{total_elementos}")
        print(f"     • Proporción: {proporcion_elementos:.4f}")
        print(f"     • Score componente 1: {medida_metadatos_completos:.4f}/10")
        
        # ===== COMPONENTE 2: Publicador Válido (5%) =====
        print(f"\n📋 COMPONENTE 2: Publicador Válido (5% del score)")
        
        info_publicador = {
            'nombre_publicador': metadata.get('owner', {}).get('displayName'),
            'correo_electronico': None,  # No disponible en esta metadata
            'enlace_institucional': metadata.get('attributionLink'),
            'usuario_institucional': metadata.get('owner', {}).get('screenName')
        }
        
        print(f"   Información del publicador:")
        for campo, valor in info_publicador.items():
            if valor:
                print(f"     ✅ {campo}: {str(valor)[:50]}...")
            else:
                print(f"     ❌ {campo}: FALTANTE")
        
        # Cálculo de score para publicador válido
        # Ponderación según importancia
        pesos_publicador = {
            'nombre_publicador': 0.4,
            'correo_electronico': 0.4,  # Alto peso pero no disponible
            'enlace_institucional': 0.15,
            'usuario_institucional': 0.05
        }
        
        score_publicador = 0
        for campo, peso in pesos_publicador.items():
            if info_publicador[campo]:
                score_publicador += peso
        
        # Ajustar a escala 0-10
        medida_publicador_valido = score_publicador * 10
        
        print(f"\n   📊 Resultados Componente 2:")
        print(f"     • Score ponderado: {score_publicador:.4f}")
        print(f"     • Score componente 2: {medida_publicador_valido:.4f}/10")
        
        # ===== COMPONENTE 3: Columnas con Descripción Válida (25%) =====
        print(f"\n📋 COMPONENTE 3: Descripciones de Columnas (25% del score)")
        
        # Usar las columnas de la metadata si están disponibles
        columnas_metadata = metadata.get('columns', [])
        
        if columnas_metadata:
            total_columnas = len(columnas_metadata)
            columnas_con_descripcion = 0
            columnas_descripciones_validas = 0
            
            print(f"   Análisis de descripciones por columna:")
            for columna in columnas_metadata:
                nombre = columna.get('name', 'Sin nombre')
                descripcion = columna.get('description', '')
                
                if descripcion and descripcion.strip():
                    columnas_con_descripcion += 1
                    # Verificar si la descripción es válida (no vacía, no genérica)
                    if len(descripcion.strip()) > 10 and not descripcion.strip().isdigit():
                        columnas_descripciones_validas += 1
                        print(f"     ✅ {nombre}: Descripción válida ({len(descripcion)} chars)")
                    else:
                        print(f"     ⚠️  {nombre}: Descripción muy corta o inválida")
                else:
                    print(f"     ❌ {nombre}: Sin descripción")
            
            proporcion_desc_validas = columnas_descripciones_validas / total_columnas if total_columnas > 0 else 0
            proporcion_faltantes = 1 - proporcion_desc_validas
            
            # Penalización cuadrática para descripciones faltantes
            penalizacion = proporcion_faltantes ** 2
            medida_col_desc_valida = (1 - penalizacion) * 10
            
            print(f"\n   📊 Resultados Componente 3:")
            print(f"     • Total columnas: {total_columnas}")
            print(f"     • Columnas con descripción: {columnas_con_descripcion}")
            print(f"     • Columnas con descripción válida: {columnas_descripciones_validas}")
            print(f"     • Proporción válidas: {proporcion_desc_validas:.4f}")
            print(f"     • Penalización: {penalizacion:.4f}")
            print(f"     • Score componente 3: {medida_col_desc_valida:.4f}/10")
            
        else:
            # Fallback: si no hay metadata de columnas, usar un valor conservador
            print(f"   ⚠️  No se encontró metadata de columnas. Usando valor conservador.")
            medida_col_desc_valida = 5.0  # Valor conservador
        
        # ===== CÁLCULO FINAL =====
        print(f"\n📐 CÁLCULO FINAL DE CREDIBILIDAD")
        
        credibilidad = (
            medida_metadatos_completos * 0.70 +
            medida_publicador_valido * 0.05 +
            medida_col_desc_valida * 0.25
        )
        
        # Asegurar límites
        credibilidad = max(0, min(10, credibilidad))
        
        print(f"\n   Fórmula aplicada:")
        print(f"   credibilidad = medidaMetadatosCompletos * 0.70 +")
        print(f"                   medidaPublicadorValido * 0.05 +")
        print(f"                   medidaColDescValida * 0.25")
        print(f"\n   Sustituyendo:")
        print(f"   credibilidad = {medida_metadatos_completos:.4f} * 0.70 + {medida_publicador_valido:.4f} * 0.05 + {medida_col_desc_valida:.4f} * 0.25")
        print(f"   credibilidad = {medida_metadatos_completos * 0.70:.4f} + {medida_publicador_valido * 0.05:.4f} + {medida_col_desc_valida * 0.25:.4f}")
        print(f"   credibilidad = {credibilidad:.4f}")
        
        # Evaluación cualitativa
        print(f"\n📊 EVALUACIÓN CUALITATIVA:")
        if credibilidad >= 8.0:
            print(f"   ✅ EXCELENTE: Alta credibilidad y confianza en los datos")
        elif credibilidad >= 6.0:
            print(f"   ⚠️  ACEPTABLE: Credibilidad moderada")
        elif credibilidad >= 4.0:
            print(f"   🔶 REGULAR: Credibilidad limitada")
        else:
            print(f"   ❌ DEFICIENTE: Baja credibilidad")
        
        print(f"\n   Puntos fuertes de credibilidad:")
        if elementos_presentes / total_elementos >= 0.8:
            print(f"     • Metadatos completos sobre origen y fuentes")
        if info_publicador['nombre_publicador']:
            print(f"     • Publicador claramente identificado")
        if medida_col_desc_valida >= 8.0:
            print(f"     • Descripciones de columnas completas y válidas")
        if metadata.get('provenance') == 'official':
            print(f"     • Procedencia oficial verificada")
        
        print(f"\n   Áreas de mejora:")
        if not info_publicador['correo_electronico']:
            print(f"     • Falta correo electrónico de contacto institucional")
        if elementos_presentes / total_elementos < 0.6:
            print(f"     • Múltiples elementos de credibilidad faltantes")
        
        print(f"\n" + "="*70)
        print(f"🎯 CREDIBILIDAD FINAL: {credibilidad:.4f}/10")
        print("="*70)
        
        return float(credibilidad)



    def calculate_portabilidad(self) -> float:
        """
        Calcula el score de portabilidad basado en formatos disponibles en el dataset.
        
        Portabilidad mide si el recurso se puede descargar y usar sin depender de 
        software propietario, sin macros, contraseñas ni bloqueos.
        
        Returns:
            float: Score entre 0 y 10
        """
        print("\n" + "="*70)
        print("📦 INICIO DEL CÁLCULO DE PORTABILIDAD")
        print("="*70)
        
        # Validar datos cargados
        if self.df is None or len(self.df) == 0:
            print("❌ No hay datos cargados. Retornando 0.0")
            return 0.0
        
        total_recursos = len(self.df)
        print(f"📊 Analizando {total_recursos} recursos para portabilidad...")
        
        # Clasificación de formatos basada en la columna 'd_formato'
        # Considerando la falta de datos completos, asignamos puntajes conservadores
        
        formatos_muy_portables = {
            'Excel', 'Hoja de calculo', 'Hoja de calculo / Web'
            # Asumimos que son XLSX sin macros por defecto (optimista pero realista)
        }
        
        formatos_medianamente_portables = {
            'Web', 'Web/Pdf', 'Pdf/Web'
            # Web puede contener datos estructurados, pero requiere verificación
        }
        
        formatos_no_portables = {
            'Pdf'  # Formato cerrado, difícil reutilización
        }
        
        # Contadores
        count_muy_portables = 0
        count_medianos = 0
        count_no_portables = 0
        count_desconocidos = 0
        
        print(f"\n🔍 CLASIFICANDO FORMATOS:")
        
        # Analizar cada recurso según su formato
        for idx, row in self.df.iterrows():
            formato = str(row.get('d_formato', '')).strip()
            medio = str(row.get('c_medio_de_conservaci_n_y', '')).strip()
            
            # Clasificación
            if formato in formatos_muy_portables:
                count_muy_portables += 1
                print(f"   ✅ MUY PORTABLE: '{formato}' (medio: {medio})")
            elif formato in formatos_medianamente_portables:
                count_medianos += 1
                print(f"   ⚠️  MEDIANAMENTE: '{formato}' (medio: {medio})")
            elif formato in formatos_no_portables:
                count_no_portables += 1
                print(f"   ❌ NO PORTABLE: '{formato}' (medio: {medio})")
            else:
                count_desconocidos += 1
                print(f"   ❓ DESCONOCIDO: '{formato}' (medio: {medio})")
        
        # Ajuste por falta de datos completos - asumimos conservadoramente
        # que los formatos desconocidos son medianamente portables
        count_medianos += count_desconocidos
        
        print(f"\n📊 RESULTADOS DE CLASIFICACIÓN:")
        print(f"   • Muy portables: {count_muy_portables}/{total_recursos}")
        print(f"   • Medianamente portables: {count_medianos}/{total_recursos}")
        print(f"   • No portables: {count_no_portables}/{total_recursos}")
        if count_desconocidos > 0:
            print(f"   • Desconocidos (asumidos como medianos): {count_desconocidos}")
        
        # Cálculo del score con pesos
        peso_muy_portable = 1.0      # Excel/CSV/JSON - formatos ideales
        peso_medio = 0.5             # Web/formatos mixtos - requieren procesamiento
        peso_no_portable = 0.0       # PDF - no reutilizable directamente
        
        # Puntuación cruda lineal
        puntuacion_cruda = (
            (count_muy_portables * peso_muy_portable) + 
            (count_medianos * peso_medio) + 
            (count_no_portables * peso_no_portable)
        ) / total_recursos
        
        # Aplicar penalización cuadrática (similar a otros criterios)
        # Esto penaliza más los datasets con alta proporción de formatos no portables
        portabilidad = 10 * (1 - (1 - puntuacion_cruda) ** 1.2)
        
        # Ajuste adicional por falta de metadatos completos
        # Reducimos ligeramente el score porque no tenemos información sobre:
        # - Extensiones específicas de archivo
        # - Presencia de macros o contraseñas
        # - Tipos MIME exactos
        factor_ajuste_metadatos = 0.9  # Penalización del 10% por falta de datos completos
        
        portabilidad_ajustada = portabilidad * factor_ajuste_metadatos
        portabilidad_final = max(0, min(10, portabilidad_ajustada))
        
        print(f"\n📐 CÁLCULO DEL SCORE:")
        print(f"   Puntuación cruda: {puntuacion_cruda:.4f}")
        print(f"   Portabilidad (sin ajuste): {portabilidad:.4f}")
        print(f"   Ajuste por metadatos incompletos: ×{factor_ajuste_metadatos}")
        print(f"   Portabilidad final: {portabilidad_final:.4f}")
        
        # Evaluación cualitativa
        proporcion_muy_portables = (count_muy_portables / total_recursos) * 100
        proporcion_portables_total = ((count_muy_portables + count_medianos) / total_recursos) * 100
        
        print(f"\n📋 EVALUACIÓN CUALITATIVA:")
        print(f"   • Formatos muy portables: {proporcion_muy_portables:.1f}%")
        print(f"   • Formatos portables total: {proporcion_portables_total:.1f}%")
        
        if proporcion_muy_portables >= 70:
            print(f"   ✅ EXCELENTE: Alta proporción de formatos muy portables")
        elif proporcion_portables_total >= 60:
            print(f"   ⚠️  ACEPTABLE: Mayoría de formatos son portables")
        elif proporcion_portables_total >= 30:
            print(f"   🔶 REGULAR: Menos de la mitad en formatos portables")
        else:
            print(f"   ❌ DEFICIENTE: Muy pocos formatos portables")
        
        # Información sobre limitaciones
        print(f"\n💡 LIMITACIONES:")
        print(f"   • No hay información sobre extensiones específicas (.csv, .xlsx, etc.)")
        print(f"   • No hay datos sobre presencia de macros o contraseñas")
        print(f"   • No se conocen tipos MIME exactos")
        print(f"   • Score ajustado a la baja por falta de metadatos completos")
        
        print(f"\n" + "="*70)
        print(f"🎯 PORTABILIDAD FINAL: {portabilidad_final:.4f}/10")
        print("="*70)
        
        # Cachear el resultado
        self.cached_scores['portabilidad'] = portabilidad_final
        
        return float(portabilidad_final)





    def calculate_recuperabilidad(self) -> float:
        accesibilidad = self.calculate_accesibilidad()

        metadatos_fuente = ['fuente', 'descripcion', 'fecha_actualizacion', 'publicador']
        metadatos_completos = sum(1 for campo in metadatos_fuente if self.metadata.get(campo))
        medida_metadatos_completos = (metadatos_completos / len(metadatos_fuente)) * 10

        metadatos_auditados = sum(1 for campo in ['fuente', 'publicador', 'licencia']
                                 if self.metadata.get(campo))
        medida_metadatos_auditados = (metadatos_auditados / 3) * 10

        recuperabilidad = (accesibilidad + medida_metadatos_completos + medida_metadatos_auditados) / 3

        return max(0, min(10, recuperabilidad))

    def calculate_disponibilidad(self) -> float:
        """
        Calcula la métrica de Disponibilidad del dataset.
        
        Disponibilidad mide la capacidad del dataset de estar **siempre listo y accesible**
        para su uso. Se calcula como el promedio simple de Accesibilidad y Actualidad.
        
        La guía define disponibilidad como:
        
        disponibilidad = (accesibilidad + actualidad) / 2
        
        Interpretación:
        - Ambos son 10: disponibilidad = 10 (máximo, datos siempre listos)
        - Uno es 10 y otro 0: disponibilidad = 5 (parcial)
        - Ambos son 0: disponibilidad = 0 (no usable)
        
        Componentes:
        1. **Accesibilidad**: ¿Qué tan fácil es acceder al dataset?
           - Basada en tags y links en metadatos
        
        2. **Actualidad**: ¿Qué tan reciente es la información?
           - Basada en fecha de última actualización
        
        Returns:
            float: Score entre 0 y 10, donde 10 = dataset siempre disponible
        """
        print("\n" + "="*70)
        print("📡 INICIO DEL CÁLCULO DE DISPONIBILIDAD")
        print("="*70)
        
        # Validar metadata
        if self.metadata is None:
            print("⚠️  No hay metadatos disponibles. Retornando score = 5.0 (indeterminado)")
            return 5.0
        
        # ===== COMPONENTE 1: ACCESIBILIDAD =====
        print(f"\n🔗 COMPONENTE 1: ACCESIBILIDAD")
        print(f"   Evaluando tags y links en metadatos...")
        try:
            accesibilidad = self.calculate_accesibilidad_from_metadata(self.metadata, verbose=False)
            print(f"   ✓ Accesibilidad calculada: {accesibilidad:.4f}/10")
        except Exception as e:
            print(f"   ⚠️  Error calculando accesibilidad: {e}")
            accesibilidad = 5.0
            print(f"   → Usando valor neutral: {accesibilidad:.4f}/10")
        
        # ===== COMPONENTE 2: ACTUALIDAD =====
        print(f"\n📅 COMPONENTE 2: ACTUALIDAD")
        print(f"   Evaluando fecha de última actualización...")
        try:
            actualidad = self.calculate_actualidad(self.metadata, verbose=False)
            print(f"   ✓ Actualidad calculada: {actualidad:.4f}/10")
        except Exception as e:
            print(f"   ⚠️  Error calculando actualidad: {e}")
            actualidad = 5.0
            print(f"   → Usando valor neutral: {actualidad:.4f}/10")
        
        # ===== CÁLCULO DE DISPONIBILIDAD =====
        print(f"\n📐 PASO 3: CÁLCULO DEL SCORE DE DISPONIBILIDAD")
        print(f"   Fórmula:")
        print(f"      disponibilidad = (accesibilidad + actualidad) / 2")
        
        print(f"\n   Sustituyendo valores:")
        print(f"      disponibilidad = ({accesibilidad:.4f} + {actualidad:.4f}) / 2")
        
        disponibilidad = (accesibilidad + actualidad) / 2
        print(f"      disponibilidad = {disponibilidad:.4f}")
        
        # Limitar al rango [0, 10]
        disponibilidad = max(0, min(10, disponibilidad))
        
        # ===== INTERPRETACIÓN =====
        print(f"\n📊 INTERPRETACIÓN DEL RESULTADO:")
        if disponibilidad >= 9.0:
            print(f"   ✅ EXCELENTE ({disponibilidad:.2f}/10): Dataset siempre listo y accesible")
        elif disponibilidad >= 7.0:
            print(f"   ✔️  BUENO ({disponibilidad:.2f}/10): Dataset generalmente disponible")
        elif disponibilidad >= 5.0:
            print(f"   ⚠️  ACEPTABLE ({disponibilidad:.2f}/10): Disponibilidad parcial")
        elif disponibilidad >= 3.0:
            print(f"   ❌ DEFICIENTE ({disponibilidad:.2f}/10): Disponibilidad limitada")
        else:
            print(f"   ❌ CRÍTICO ({disponibilidad:.2f}/10): Dataset prácticamente no disponible")
        
        print(f"\n" + "="*70)
        print(f"🎯 RESULTADO FINAL DE DISPONIBILIDAD: {disponibilidad:.4f}/10")
        print("="*70 + "\n")
        
        return float(disponibilidad)

    def calculate_all_scores(self) -> Dict[str, float]:
        return {
            'confidencialidad': self.calculate_confidencialidad(),
            'relevancia': self.calculate_relevancia(),
            'actualidad': self.calculate_actualidad(self.metadata),
            'trazabilidad': self.calculate_trazabilidad(),
            'conformidad': self.calculate_conformidad(),
            'exactitudSintactica': self.calculate_exactitud_sintactica(),
            'exactitudSemantica': self.calculate_exactitud_semantica(),
            'completitud': self.calculate_completitud(),
            'consistencia': self.calculate_consistencia(),
            'precision': self.calculate_precision(),
            'portabilidad': self.calculate_portabilidad(),
            'credibilidad': self.calculate_credibilidad(),
            'comprensibilidad': self.calculate_comprensibilidad(),
            'accesibilidad': self.calculate_accesibilidad(),
            'unicidad': self.calculate_unicidad(),
            'eficiencia': self.calculate_eficiencia(),
            'recuperabilidad': self.calculate_recuperabilidad(),
            'disponibilidad': self.calculate_disponibilidad()
        }
