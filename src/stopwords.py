"""
stopwords.py
============
Lista de palabras vacias (stopwords) en espanol e ingles.

El corpus de 505 documentos esta en ingles (testimonios y comunicados del
Center for Democracy and Technology), pero los ejemplos de la actividad
usan tokens en espanol (perro, gato, pato). Se cargan ambos idiomas para
que el indexador funcione con cualquiera de los dos sin reconfigurarse.

Las palabras estan escritas sin acentos porque el tokenizador quita los
acentos ANTES de consultar este conjunto.
"""

_ESPANOL = """
a al algo algun alguna algunas alguno algunos ante antes aquel aquella
aquellas aquello aquellos aqui asi aun aunque bajo bien cada casi como
con contra cual cuales cuando cuanto cuanta cuantas cuantos de del demas
desde donde dos el ella ellas ello ellos en entre era eran eres es esa
esas ese eso esos esta estaba estaban estan estar estas este esto estos
estoy fue fueron fui ha habia han hasta hay he incluso la las le les lo
los mas me mi mia mias mio mios mis mismo mucho muy nada ni no nos
nosotros nuestra nuestras nuestro nuestros o os otra otras otro otros
para pero poco por porque pues que quien quienes se sea sean segun ser
si sido sin sobre sola solas solo solos son su sus suya suyas suyo suyos
tal tambien tanto te tener tengo ti tiene tienen toda todas todo todos
tras tu tus tuya tuyas tuyo tuyos un una unas uno unos usted ustedes va
van vosotros voy vuestra vuestras vuestro vuestros y ya yo
"""

_INGLES = """
about above after again against all am an and any are aren as at be
because been before being below between both but by can cannot could
couldn did didn do does doesn doing don down during each few for from
further had hadn has hasn have haven having he her here hers herself him
himself his how however if in into is isn it its itself just me more
most mustn my myself no nor not of off on once only or other ought our
ours ourselves out over own same shan she should shouldn so some such
than that the their theirs them themselves then there these they this
those through to too under until up very was wasn we were weren what
when where which while who whom why will with won would wouldn you your
yours yourself yourselves
"""

STOPWORDS: frozenset[str] = frozenset(_ESPANOL.split()) | frozenset(_INGLES.split())
