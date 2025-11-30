import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000

def read_adc(channel):
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc[1] & 3) << 8) + adc[2]

print("MCP3008 Diagnostic Test")
print("Checking all channels...")
print()

while True:
    values = []
    for ch in range(8):
        val = read_adc(ch)
        values.append(val)
    
    print(f"CH0:{values[0]:4d} CH1:{values[1]:4d} CH2:{values[2]:4d} CH3:{values[3]:4d} CH4:{values[4]:4d} CH5:{values[5]:4d} CH6:{values[6]:4d} CH7:{values[7]:4d}")
    time.sleep(0.2)