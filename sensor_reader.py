"""
Background thread reads 8 ADC channels at 100Hz
Hit detection threshold: ADC > 100
Damage formula: damage = min(max((adc_value - 100) / 10, 5), 50)

"""