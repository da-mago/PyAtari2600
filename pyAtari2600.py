import numpy as np
import pygame

#
# ATARI 2600 core
#

A = X = Y = 0                      # Registers
PC = 0                             # Program counter
SP = 0                             # Stack pointer
N = V = B = D = I = Z = C = 0      # Status flags
memory = [0 for x in range(2**13)] # Memory map
num_cycles = 0                     # Atari clock cycles
page_crossed = 0
line = 0
screen = np.zeros((160, 192, 3), dtype=np.uint8)
colubk = [[0,0]] # List of background colour changes during the line
# Playfield (40 bits)
pf0_1 = pf0_2 = pf1_1 = pf1_2 = pf2_1 = pf2_1 = 0
pf_mirror = 0
# Sprites
P0_pos = P1_pos = M0_pos = M1_pos = BL_pos = 0
#
TIA_UPDATE = False
tia_addr  = 0
tia_value = 0

MAX_MEM_ADDR = 0x1fff # 8KB-1 (13-bits)
STACK_ADDR   = 0x100

# NTSC
NTSC_colorMap = [0x000000, 0x404040, 0x6C6C6C, 0x909090, 0xB0B0B0, 0xC8C8C8, 0xDCDCDC, 0xECECEC, 
                 0x444400, 0x646410, 0x848424, 0xA0A034, 0xB8B840, 0xD0D050, 0xE8E85C, 0xFCFC68,
                 0x702800, 0x844414, 0x985C28, 0xAC783C, 0xBC8C4C, 0xCCA05C, 0xDCB468, 0xECC878,
                 0x841800, 0x983418, 0xAC5030, 0xC06848, 0xD0805C, 0xE09470, 0xECA880, 0xFCBC94,
                 0x880000, 0x9C2020, 0xB03C3C, 0xC05858, 0xD07070, 0xE08888, 0xECA0A0, 0xFCB4B4,
                 0x78005C, 0x8C2074, 0xA03C88, 0xB0589C, 0xC070B0, 0xD084C0, 0xDC9CD0, 0xECB0E0,
                 0x480078, 0x602090, 0x783CA4, 0x8C58B8, 0xA070CC, 0xB484DC, 0xC49CEC, 0xD4B0FC,
                 0x140084, 0x302098, 0x4C3CAC, 0x6858C0, 0x7C70D0, 0x9488E0, 0xA8A0EC, 0xBCB4FC,
                 0x000088, 0x1C209C, 0x3840B0, 0x505CC0, 0x6874D0, 0x7C8CE0, 0x90A4EC, 0xA4B8FC,
                 0x00187C, 0x1C3890, 0x3854A8, 0x5070BC, 0x6888CC, 0x7C9CDC, 0x90B4EC, 0xA4C8FC,
                 0x002C5C, 0x1C4C78, 0x386890, 0x5084AC, 0x689CC0, 0x7CB4D4, 0x90CCE8, 0xA4E0FC,
                 0x003C2C, 0x1C5C48, 0x387C64, 0x509C80, 0x68B494, 0x7CD0AC, 0x90E4C0, 0xA4FCD4,
                 0x003C2C, 0x1C5C48, 0x387C64, 0x509C80, 0x68B494, 0x7CD0AC, 0x90E4C0, 0xA4FCD4,
                 0x003C00, 0x205C20, 0x407C40, 0x5C9C5C, 0x74B474, 0x8CD08C, 0xA4E4A4, 0xB8FCB8,
                 0x143800, 0x345C1C, 0x507C38, 0x6C9850, 0x84B468, 0x9CCC7C, 0xB4E490, 0xC8FCA4,
                 0x2C3000, 0x4C501C, 0x687034, 0x848C4C, 0x9CA864, 0xB4C078, 0xCCD488, 0xE0EC9C,
                 0x442800, 0x644818, 0x846830, 0xA08444, 0xB89C58, 0xD0B46C, 0xE8CC7C, 0xFCE08C ]

colorMap = [[color>>16, (color>>8)&0xff, color&0xff] for color in NTSC_colorMap]
#print colorMap

#
# TIA registers
#
# Only Write
VSYNC  = 0x00 #  0000 00x0   Vertical Sync Set-Clear
VBLANK = 0x01 #  xx00 00x0   Vertical Blank Set-Clear
WSYNC  = 0x02 #  ---- ----   Wait for Horizontal Blank
RSYNC  = 0x03 #  ---- ----   Reset Horizontal Sync Counter
NUSIZ0 = 0x04 #  00xx 0xxx   Number-Size player/missle 0
NUSIZ1 = 0x05 #  00xx 0xxx   Number-Size player/missle 1
COLUP0 = 0x06 #  xxxx xxx0   Color-Luminance Player 0
COLUP1 = 0x07 #  xxxx xxx0   Color-Luminance Player 1
COLUPF = 0x08 #  xxxx xxx0   Color-Luminance Playfield
COLUBK = 0x09 #  xxxx xxx0   Color-Luminance Background
CTRLPF = 0x0A #  00xx 0xxx   Control Playfield, Ball, Collisions
REFP0  = 0x0B #  0000 x000   Reflection Player 0
REFP1  = 0x0C #  0000 x000   Reflection Player 1
PF0    = 0x0D #  xxxx 0000   Playfield Register Byte 0
PF1    = 0x0E #  xxxx xxxx   Playfield Register Byte 1
PF2    = 0x0F #  xxxx xxxx   Playfield Register Byte 2
RESP0  = 0x10 #  ---- ----   Reset Player 0
RESP1  = 0x11 #  ---- ----   Reset Player 1
RESM0  = 0x12 #  ---- ----   Reset Missle 0
RESM1  = 0x13 #  ---- ----   Reset Missle 1
RESBL  = 0x14 #  ---- ----   Reset Ball
AUDC0  = 0x15 #  0000 xxxx   Audio Control 0
AUDC1  = 0x16 #  0000 xxxx   Audio Control 1
AUDF0  = 0x17 #  000x xxxx   Audio Frequency 0
AUDF1  = 0x18 #  000x xxxx   Audio Frequency 1
AUDV0  = 0x19 #  0000 xxxx   Audio Volume 0
AUDV1  = 0x1A #  0000 xxxx   Audio Volume 1
GRP0   = 0x1B #  xxxx xxxx   Graphics Register Player 0
GRP1   = 0x1C #  xxxx xxxx   Graphics Register Player 1
ENAM0  = 0x1D #  0000 00x0   Graphics Enable Missle 0
ENAM1  = 0x1E #  0000 00x0   Graphics Enable Missle 1
ENABL  = 0x1F #  0000 00x0   Graphics Enable Ball
HMP0   = 0x20 #  xxxx 0000   Horizontal Motion Player 0
HMP1   = 0x21 #  xxxx 0000   Horizontal Motion Player 1
HMM0   = 0x22 #  xxxx 0000   Horizontal Motion Missle 0
HMM1   = 0x23 #  xxxx 0000   Horizontal Motion Missle 1
HMBL   = 0x24 #  xxxx 0000   Horizontal Motion Ball
VDELP0 = 0x25 #  0000 000x   Vertical Delay Player 0
VDELP1 = 0x26 #  0000 000x   Vertical Delay Player 1
VDELBL = 0x27 #  0000 000x   Vertical Delay Ball
RESMP0 = 0x28 #  0000 00x0   Reset Missle 0 to Player 0
RESMP1 = 0x29 #  0000 00x0   Reset Missle 1 to Player 1
HMOVE  = 0x2A #  ---- ----   Apply Horizontal Motion
HMCLR  = 0x2B #  ---- ----   Clear Horizontal Move Registers
CXCLR  = 0x2C #  ---- ----   Clear Collision Latches

# Only read
CXM0P  = 0x00 #  xx00 0000   Read Collision  M0-P1   M0-P0
CXM1P  = 0x01 #  xx00 0000                   M1-P0   M1-P1
CXP0FB = 0x02 #  xx00 0000                   P0-PF   P0-BL
CXP1FB = 0x03 #  xx00 0000                   P1-PF   P1-BL
CXM0FB = 0x04 #  xx00 0000                   M0-PF   M0-BL
CXM1FB = 0x05 #  xx00 0000                   M1-PF   M1-BL
CXBLPF = 0x06 #  x000 0000                   BL-PF   -----
CXPPMM = 0x07 #  xx00 0000                   P0-P1   M0-M1
INPT0  = 0x08 #  x000 0000   Read Pot Port 0
INPT1  = 0x09 #  x000 0000   Read Pot Port 1
INPT2  = 0x0A #  x000 0000   Read Pot Port 2
INPT3  = 0x0B #  x000 0000   Read Pot Port 3
INPT4  = 0x0C #  x000 0000   Read Input (Trigger) 0
INPT5  = 0x0D #  x000 0000   Read Input (Trigger) 1


def TIA_update():
    global memory
    global ncycles
    global P0_pos, P1_pos, M0_pos, M1_pos, BL_pos
    
    addr  = tia_addr
    value = tia_value

    # Trigger registers (ignore value)
    if addr == WSYNC:
        global num_cycles
        num_cycles = 228 # NTSC

    elif addr == VSYNC:
        global  line
        if value == 0:
            line = 3
            print 'VSYNC'

    elif addr == RSYNC:
        pass

    elif addr == RESP0:
        P0_pos = num_cycles # Assume one change max per line

    elif addr == RESP1:
        P1_pos = num_cycles

    elif addr == RESM0:
        M0_pos = num_cycles

    elif addr == RESM1:
        M1_pos = num_cycles

    elif addr == RESBL:
        BL_pos = num_cycles

    elif addr == HMOVE:
        tmp = memory[HMP0] >> 4
        if tmp >= 8: tmp = tmp - 16   # -8 ... +7
        P0_pos += tmp
        tmp = memory[HMP1] >> 4
        if tmp >= 8: tmp = tmp - 16
        P1_pos += tmp
        tmp = memory[HMM0] >> 4
        if tmp >= 8: tmp = tmp - 16
        M0_pos += tmp
        tmp = memory[HMM1] >> 4
        if tmp >= 8: tmp = tmp - 16
        M1_pos += tmp
        tmp = memory[HMBL] >> 4
        if tmp >= 8: tmp = tmp - 16
        BL_pos += tmp

    elif addr == HMCLR:
        memory[HMP0] = 0
        memory[HMP1] = 0
        memory[HMM0] = 0
        memory[HMM1] = 0
        memory[HMBL] = 0

    elif addr == CXCLR:
        pass

    elif addr == PF0:
        global pf0_1, pf0_2
        if num_cycles < 48:
            pf0_1 = value
            pf0_2 = value
        elif num_cycles < 148:
            pf0_2 = value

    elif addr == PF1:
        global pf1_1, pf1_2
        if num_cycles < 84:
            pf1_1 = value
            pf1_2 = value
        elif num_cycles < 164:
            pf1_2 = value

    elif addr == PF2:
        global pf2_1, pf2_2
        if num_cycles < 116:
            pf2_1 = value
            pf2_2 = value
        elif num_cycles < 196:
            pf2_2 = value

    elif addr == CTRLPF:
        if num_cycles < 144: # Before half-line
            pf_mirror = 1 if value & 0x01 else 0

    elif addr == COLUBK:
        global colubk
        #cycles = num_cycles - 68 if num_cycles >= 68 else 0
        #colubk.append([cycles, value])
        if num_cycles >= 68:
            colubk.append([num_cycles - 68, value])
        else:
            colubk[0] = [0, value]

    elif addr == COLUPF:
        pass


# Memory bus operation
def MEM_WRITE(addr, value):
    global memory
    memory[addr] = value
    
    # TIA register (0x00 - 0x80)
    if addr < 0x80:
        global TIA_UPDATE, tia_addr, tia_value
        TIA_UPDATE = True
        tia_addr  = addr
        tia_value = value

            
def MEM_READ(addr):
    return memory[addr]




# Addressing modes
# READ
def NONE(val):
    return 0

def IMMEDIATE(val):
    return val

def RELATIVE(addr):
    if addr < 128:
        return addr
    else:
        return (addr - 0x100)

def MEM_READ_ZEROPAGE(addr):
    return addr

def MEM_READ_ZEROPAGE_X(addr):
    return (addr + X) & 0xff

def MEM_READ_ZEROPAGE_Y(addr):
    return (addr + Y) & 0xff

def MEM_READ_ABSOLUTE(addr):

    return addr & MAX_MEM_ADDR

# Not clear the 'page_crossed' extra cycle: https://wiki.nesdev.com/w/index.php/CPU_addressing_modes
def MEM_READ_ABSOLUTE_X(addr):
    global page_crossed

    addr = addr + X
    if (addr & 0xff) < X: page_crossed = 1
    return addr & MAX_MEM_ADDR

def MEM_READ_ABSOLUTE_Y(addr):
    global page_crossed

    addr = addr + Y
    if (addr & 0xff) < Y: page_crossed = 1
    return addr & MAX_MEM_ADDR

def MEM_READ_INDIRECT(addrL):
    # HW Bug in original 6502 processor (instead of addrH = addrL+1)
    addrH = (addrL & 0xff00) | ((addrL + 1) & 0x00ff)
    addr = memory[addrL] | (memory[addrH]<<8)

    return MEM_READ(addr & MAX_MEM_ADDR)

def MEM_READ_INDIRECT_X(addr):
    addr = (addr + X) & 0xff
    addr = memory[addr] | (memory[(addr + 1) & 0xff] << 8)
    return addr & MAX_MEM_ADDR

def MEM_READ_INDIRECT_Y(addr):
    global page_crossed
    
    addr = memory[addr] | (memory[(addr + 1) & 0xff] << 8)
    addr = addr + Y
    if (addr & 0xff) < Y: page_crossed = 1
    return addr & MAX_MEM_ADDR

#TODO: maybe delete this macros
# WRITE
def MEM_WRITE_ZEROPAGE(addr, val):
    MEM_WRITE(addr, val)

def MEM_WRITE_ZEROPAGE_X(addr, val):
    MEM_WRITE((addr +  X) & 0xff, val)
#
def MEM_WRITE_ZEROPAGE_Y(addr, val):
    MEM_WRITE((addr +  Y) & 0xff, val)

def MEM_WRITE_ABSOLUTE(addr, val):
    MEM_WRITE(addr & MAX_MEM_ADDR, val)

def MEM_WRITE_ABSOLUTE_X(addr, val):
    MEM_WRITE((addr + X) & MAX_MEM_ADDR, val)    

def MEM_WRITE_ABSOLUTE_Y(addr, val):
    MEM_WRITE((addr + Y) & MAX_MEM_ADDR, val)    
    
#def MEM_WRITE_MEM_READ_INDIRECT(addr, val):
#    addr = memory[addr] | memory[addr + 1]<<8
#    MEM_WRITE(addr & MAX_MEM_ADDR, val)
    
def MEM_WRITE_INDIRECT_X(addr, val):
    addr = (addr+ X) & 0xff
    addr = memory[addr] | (memory[addr+1]<<8)
    MEM_WRITE(addr & MAX_MEM_ADDR, val)

def MEM_WRITE_INDIRECT_Y(addr, val):
    addr = memory[addr] | (memory[addr+1]<<8)
    addr = addr + Y
    MEM_WRITE(addr & MAX_MEM_ADDR, val)

# Flags status byte
def PSW_GET():
    tmp = 0
    if C == True: tmp |= 0x01 # inventado..mirar status byte 
    if Z == True: tmp |= 0x02
    if I == True: tmp |= 0x04
    if D == True: tmp |= 0x08
    if B == True: tmp |= 0x10
    if V == True: tmp |= 0x20
    if N == True: tmp |= 0x40
    return tmp

def PSW_SET(val):
    global C,Z,I,D,B,V,N
    
    C = val&0x01 != 0
    Z = val&0x02 != 0
    I = val&0x04 != 0
    D = val&0x08 != 0
    B = val&0x10 != 0
    V = val&0x20 != 0
    N = val&0x40 != 0
    
    
# Opcodes definition
#

# Unknown opcode
def unknown(unused):
    print "opcode not implemented"
    return 0

# ADC
def adc_(val):
    global A
    global V, C, Z, N

    res = A + val + C
    C = res > 255
    res &= 0xff
    V = (A^res)&(val^res)&0x80 != 0
    Z = res == 0
    N = (res & 0x80) != 0
    A = res

    return 0

def adcMem_(addr):
    return adc_(MEM_READ(addr))

# AND
def and_(val):
    global A
    global Z,N

    A = (A & val)
    Z = (A == 0)
    N = (A & 0x80) != 0

    return 0

def andMem_(addr):
    return andMem_(MEM_READ(addr))

# ASL
def aslAcc_(unused):
    global A
    global Z,N,C

    res = A << 1
    A = res & 0xff
    C = (res > 0xff)
    Z = (A == 0)
    N = (A & 0x80) != 0

    return 0


def aslMem_(addr):
    global Z,N,C

    res = MEM_READ(addr) << 1
    val = res & 0xff
    MEM_WRITE(addr, val)
    C = (res > 0xff)
    Z = (val == 0)
    N = (val & 0x80) != 0

    return 0

# Any branch
def bAny_(taken):
    global PC

    if taken:
        curr_PC = PC
        PC     += addr
        extra_cycles = 2 if ((curr_PC & 0xff00) != (PC & 0xff00)) else 1
    else:
        extra_cycles = 0

    return extra_cycles

# BCC
def bcc_(unused):
    return bAny_(C == False)

# BCS
def bcs_(unused):
    return bAny_(C == True)

# BEQ
def beq_(unused):
    return bAny_(Z == True)

# BIT
def bit_(addr):
    global Z, V, N

    val = MEM_READ(addr)
    Z = (val & A) == 0
    V = (val & 0x40) != 0
    N = (val & 0x80) != 0

    return 0

# BMI
def bmi_(unused):
    return bAny_(N == True)

# BNE
def bne_(unused):
    return bAny_(Z == False)

# BPL
def bpl_(unused):
    return bAny_(N == False)

# BRK
def brk_(unused):
    global PC, SP
    global B

    B = 1
    # push PC and SP to stack
    rti_PC = PC + 1
    memory[STACK_ADDR + SP]     = rti_PC & 0xff
    memory[STACK_ADDR + SP - 1] = rti_PC >> 8
    memory[STACK_ADDR + SP - 2] = PSW_GET()
    SP -= 3
    # PC = interrupt vector
    PC = MEM_READ_ABSOLUTE(0xfffe) | MEM_READ_ABSOLUTE(0xffff)<<8 

    return 0

# BVC
def bvc_(unused):
    return bAny_(V == False)

# BVC
def bvs_(unused):
    return bAny_(V == True)

# CLC
def clc_(val):
    global C

    C = False

    return 0

# CLD
def cld_(val):
    global D

    D = False

    return 0    

# CLI
def cli_(val):
    global I

    I = False

    return 0

# CLV
def clv_(val):
    global V

    V = False

    return 0
    
# CMP
def cmp_(val):
    global Z, C, N

    Z = A == val
    C = A >= val
    N = (((A - val)%256) & 0x80) != 0

    return 0

def cmpMem_(addr):
    return cmp_(MEM_READ(addr))

# CPX
def cpx_(val):
    global Z, C, N

    Z = X == val
    C = X >= val
    N = (((X - val)%256) & 0x80) != 0

    return 0

def cpxMem_(addr):
    return cpx_(MEM_READ(addr))

# CPY
def cpy_(val):
    global Z, C, N

    Z = Y == val
    C = Y >= val
    N = (((Y - val)%256) & 0x80) != 0

    return 0

def cpyMem_(addr):
    return cpy_(MEM_READ(addr))

# DEC
def decMem_(addr):
    global Z, N

    val = (MEM_READ(addr) - 1) & 0xff
    MEM_WRITE(addr, val)
    Z = val == 0
    N = (val & 0x80) != 0

    return 0

# DEX
def dex_(val):
    global X
    global Z, N

    X = (X - 1) & 0xff
    Z = X == 0
    N = (X & 0x80) != 0

    return 0

# DEY
def dey_(val):
    global Y
    global Z, N

    Y = (Y - 1) & 0xff 
    Z = Y == 0
    N = (Y & 0x80) != 0

    return 0

# EOR
def eor_(val):
    global A
    global Z, N

    A ^= val
    Z = A == 0
    N = (A & 0x80) != 0

    return page_crossed

def eorMem_(addr):
    val = MEM_READ(addr)
    A ^= val
    Z = A == 0
    N = (A & 0x80) != 0

# INC
def incMem_(addr):
    global Z, N

    val = (MEM_READ(addr) + 1) & 0xff
    MEM_WRITE_ZEROPAGE(addr, val)
    Z = val == 0
    N = (val & 0x80) != 0

    return 0

def inx_(val):    
    global X
    global Z, N

    X = (X + 1) & 0xff
    Z = X == 0
    N = (X & 0x80) != 0

    return 0

def iny_(val):    
    global Y
    global Z, N

    Y = (Y + 1) & 0xff
    Z = Y == 0
    N = (Y & 0x80) != 0

    return 0

# JMP
def jmp_(val):    
    global PC
    
    PC = val & MAX_MEM_ADDR

    return 0
    
# JSR
def jsr_(val):
    global PC, SP
    global memory
    #print(hex(val & MAX_MEM_ADDR))
    # push PC-1 on to the stack
    PC -= 1
    memory[STACK_ADDR + SP]     = PC & 0xff
    memory[STACK_ADDR + SP - 1] = PC >> 8
    SP -= 2
    # update PC
    PC = val

    return 0

# LDA
def lda_(val):    
    global A
    global Z, N

    A = val
    Z = A == 0
    N = (A & 0x80) != 0
    
    return 0

def ldaMem_(addr):    
    return lda_(MEM_READ(addr))

# LDX
def ldx_(val):    
    global X
    global Z, N

    X = val
    Z = X == 0
    N = (X & 0x80) != 0

    return 0

def ldxMem_(addr):
    return ldx_(MEM_READ(addr))

# LDY
def ldy_(val):    
    global Y
    global Z,N

    Y = val
    Z = Y == 0
    N = (Y & 0x80) != 0

    return 0

def ldyMem_(addr):
    return ldy_(MEM_READ(addr))

# LSR
def lsr_(unused):
    global Z, N
    
    C = (A & 0x01) != 0
    A = A >> 1
    Z = (A == 0)
    N = (A & 0x80) != 0
    
    return 0

def lsrMem_(addr):
    global Z, N
    
    val = MEM_READ(addr)
    C = (val & 0x01) != 0
    val = val >> 1
    MEM_WRITE(addr, val)
    Z = (val == 0)
    N = (val & 0x80) != 0
    
    return 0

def nop_(val):    
    return 0    

def ora_(val):    
    global A
    global Z,N

    A = A | val
    Z = (A == 0)
    N = (A & 0x80) != 0

    return 0

def oraMem_(addr):    
    return ora_(MEM_READ(addr))

def pha_(val):    
    global SP
    global memory

    memory[STACK_ADDR + SP] = A
    SP = SP - 1

    return 0    

def php_(val):
    global SP
    global memory

    memory[STACK_ADDR + SP] = PSW_GET()
    SP = SP - 1

    return 0    

def pla_(val):
    global A, SP
    global Z, N

    SP = SP + 1
    A = memory[STACK_ADDR + SP]
    Z = A == 0 
    N = (A & 0x80 != 0) 

    return 0

def plp_(val):
    global SP
    global C,Z,I,D,B,V,N

    SP = SP + 1
    tmp = memory[STACK_ADDR + SP]
    PSW_SET(tmp)

    return 0

# ROL
def rol_(val):
    global Z,N,C

    res = (A << 1) | C # Mixing integer and boolean, but it is OK (True -> 1)
    A = res & 0xff
    C = res > 0xff
    Z = (A == 0)
    N = (A & 0x80) != 0    

    return res 

def rolMem_(addr):
    global Z,N,C

    res = (MEM_READ(addr) << 1) | C
    val = res & 0xff
    MEM_WRITE(addr, val)
    C = res > 0xff
    Z = (val == 0)
    N = (val & 0x80) != 0    

    return res 

# ROR
def ror_(val):
    global Z,C,N
    
    bit0 = val & 0x01
    A = (val >> 1) | (C << 7) # Mixing integer and boolean, but it is OK (True -> 1)
    N = C
    C = (bit0 != 0)
    Z = (A == 0)
    
    return res

def rorMem_(addr):
    global Z,C,N
    
    val = MEM_READ(addr)
    bit0 = val & 0x01
    res = (val >> 1) | (C << 7)
    MEM_WRITE(addr, res)
    N = C
    C = (bit0 != 0)
    Z = (res == 0)
    
    return res


# RTI
def rti_(unused):
    global PC, SP
    global C,Z,I,D,B,V,N

    PSW_SET(memory[STACK_ADDR + SP])
    PC = memory[STACK_ADDR + SP + 1] | (memory[STACK_ADDR + SP + 2] << 8)
    SP += 3

    return 0

# RTS
def rts_(unused):
    global PC, SP

    PC = (memory[STACK_ADDR + SP] | (memory[STACK_ADDR + SP + 1] << 8)) - 1
    SP += 2

    return 0

# SBC (DMG: flags not implemented)
def sbc_(val):
    global A
    global Z,C,V,N

    res = A - val
    if not C: res -= 1
    
    A = res & 0xff
    Z = A == 0
    #C = ?
    #V = ?
    N = (A & 0x80) != 0

    return page_crossed

# SEC
def sec_(val):
    global C

    C = 1

    return 0

# SED
def sed_(val):
    global D

    D = 1

    return 0    

# SEI
def sei_(val):
    global I

    I = 1

    return 0

# STA
def staZP_(val):

    MEM_WRITE_ZEROPAGE(val, A)

    return 0

def staZPX_(val):

    MEM_WRITE_ZEROPAGE_X(val, A)

    return 0    

def staABS_(val):

    MEM_WRITE_ABSOLUTE(val, A)

    return 0

def staABSX_(val):

    MEM_WRITE_ABSOLUTE_X(val, A)

    return 0

def staABSY_(val):

    MEM_WRITE_ABSOLUTE_Y(val, A)

    return 0    

def staINDX_(val):

    MEM_WRITE_INDIRECT_X(val, A)

    return 0

def staINDY_(val):

    MEM_WRITE_INDIRECT_Y(val, A)

    return 0    

# STX
def stxZP_(val):

    MEM_WRITE_ZEROPAGE(val, X)

    return 0

def stxZPY_(val):

    MEM_WRITE_ZEROPAGE_X(val, X)

    return 0    

def stxABS_(val):

    MEM_WRITE_ABSOLUTE(val, X)

    return 0

# STY
def styZP_(val):

    MEM_WRITE_ZEROPAGE(val, Y)

    return 0

def styZPX_(val):

    MEM_WRITE_ZEROPAGE_X(val, Y)

    return 0    

def styABS_(val):

    MEM_WRITE_ABSOLUTE(val, Y)

    return 0

# TAX
def tax_(unused):
    global X
    global Z, N

    X = A
    Z = X == 0
    N = (X & 0x80) != 0

    return 0

# TAY
def tay_(unused):
    global Y
    global Z, N

    Y = A
    Z = Y == 0
    N = (Y & 0x80) != 0

    return 0    

# TSX
def tsx_(unused):
    global X
    global Z, N

    X = SP
    Z = X == 0
    N = (X & 0x80) != 0

    return 0

# TSA
def tsa_(unused):
    global A
    global Z, N

    A = X
    Z = A == 0
    N = (A & 0x80) != 0

    return 0

# TXS
def txs_(unused):
    global SP

    SP = X

    return 0    

# TYA
def tya_(unused):
    global A
    global Z, N

    A = Y
    Z = A == 0
    N = (A & 0x80) != 0

    return 0    



# opcodes table
opcode_table = [[unknown, IMMEDIATE, 0, 0] for x in range(256)]
#                    [operation, Addresing mode,        bytes, cycles, add_page_crossed]
# ADD
opcode_table[0x69] = [adc_,      IMMEDIATE,             2,     2,      0]
opcode_table[0x65] = [adcMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0x75] = [adcMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0x6d] = [adcMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0x7d] = [adcMem_,   MEM_READ_ABSOLUTE_X,   3,     4,      1]
opcode_table[0x79] = [adcMem_,   MEM_READ_ABSOLUTE_Y,   3,     4,      1]
opcode_table[0x61] = [adcMem_,   MEM_READ_INDIRECT_X,   2,     6,      0]
opcode_table[0x71] = [adcMem_,   MEM_READ_INDIRECT_Y,   2,     5,      1]

# AND
opcode_table[0x29] = [and_,      IMMEDIATE,             2,     2,      0]
opcode_table[0x25] = [andMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0x35] = [andMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0x2d] = [andMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0x3d] = [andMem_,   MEM_READ_ABSOLUTE_X,   3,     4,      1]
opcode_table[0x39] = [andMem_,   MEM_READ_ABSOLUTE_Y,   3,     4,      1]
opcode_table[0x21] = [andMem_,   MEM_READ_INDIRECT_X,   2,     6,      0]
opcode_table[0x31] = [andMem_,   MEM_READ_INDIRECT_Y,   2,     5,      1]

# ASL
opcode_table[0x0a] = [aslAcc_,   IMMEDIATE,             1,     2,      0]
opcode_table[0x06] = [aslMem_,   MEM_READ_ZEROPAGE,     2,     5,      0]
opcode_table[0x16] = [aslMem_,   MEM_READ_ZEROPAGE_X,   2,     6,      0]
opcode_table[0x0e] = [aslMem_,   MEM_READ_ABSOLUTE,     3,     6,      0]
opcode_table[0x1e] = [aslMem_,   MEM_READ_ABSOLUTE_X,   3,     7,      0]

# BCC                                                
opcode_table[0x90] = [bcc_,      RELATIVE,              2,     2,      0]

# BCS                                                   
opcode_table[0xb0] = [bcs_,      RELATIVE,              2,     2,      0]

# BEQ                                                   
opcode_table[0xf0] = [beq_,      RELATIVE,              2,     2,      0]

# BIT
opcode_table[0x24] = [bit_,      MEM_READ_ZEROPAGE,     2,     2,      0]
opcode_table[0x2c] = [bit_,      MEM_READ_ABSOLUTE,     2,     2,      0]

# BMI
opcode_table[0x30] = [bmi_,      RELATIVE,              2,     2,      0]

# BNE                                                   
opcode_table[0xd0] = [bne_,      RELATIVE,              2,     2,      0]

# BPL                                                   
opcode_table[0x10] = [bpl_,      RELATIVE,              2,     2,      0]

# BRK                                                   
opcode_table[0x00] = [brk_,      NONE,                  1,     7,      0]

# BVC                                                   
opcode_table[0x50] = [bvc_,      RELATIVE,              2,     2,      0]

# BVS
opcode_table[0x70] = [bvs_,      RELATIVE,              2,     2,      0]

# CLC                                                   
opcode_table[0x18] = [clc_,      NONE,                  1,     2,      0]

# CLD                                                   
opcode_table[0xd8] = [cld_,      NONE,                  1,     2,      0]

# CLI                                                   
opcode_table[0x58] = [cli_,      NONE,                  1,     2,      0]

# CLV                                                   
opcode_table[0xb8] = [clv_,      NONE,                  1,     2,      0]

# CMP                                                
opcode_table[0xc9] = [cmp_,      IMMEDIATE,             2,     2,      0]
opcode_table[0xc5] = [cmpMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0xd5] = [cmpMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0xcd] = [cmpMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0xdd] = [cmpMem_,   MEM_READ_ABSOLUTE_X,   3,     4,      0]
opcode_table[0xd9] = [cmpMem_,   MEM_READ_ABSOLUTE_Y,   3,     4,      0]
opcode_table[0xc1] = [cmpMem_,   MEM_READ_INDIRECT_X,   2,     6,      0]
opcode_table[0xd1] = [cmpMem_,   MEM_READ_INDIRECT_Y,   2,     5,      0]

# CPX
opcode_table[0xe0] = [cpx_,      IMMEDIATE,             2,     2,      0]
opcode_table[0xe4] = [cpxMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0xec] = [cpxMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]

# CPY
opcode_table[0xc0] = [cpy_,      IMMEDIATE,             2,     2,      0]
opcode_table[0xc4] = [cpyMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0xcc] = [cpyMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]

# DEC
opcode_table[0xc6] = [decMem_,   MEM_READ_ZEROPAGE,     2,     5,      0]
opcode_table[0xd6] = [decMem_,   MEM_READ_ZEROPAGE_X,   2,     6,      0]
opcode_table[0xce] = [decMem_,   MEM_READ_ABSOLUTE,     3,     6,      0]
opcode_table[0xde] = [decMem_,   MEM_READ_ABSOLUTE_X,   3,     7,      0]

# DEX
opcode_table[0xca] = [dex_,      MEM_READ_ZEROPAGE,     1,     2,      0]

# DEY
opcode_table[0x88] = [dey_,      MEM_READ_ZEROPAGE,     1,     2,      0]

# EOR
opcode_table[0x49] = [eor_,      IMMEDIATE,              2,     2,      0]
opcode_table[0x45] = [eorMem_,   MEM_READ_ZEROPAGE,      2,     3,      0]
opcode_table[0x55] = [eorMem_,   MEM_READ_ZEROPAGE_X,    2,     4,      0]
opcode_table[0x4d] = [eorMem_,   MEM_READ_ABSOLUTE,      3,     4,      0]
opcode_table[0x5d] = [eorMem_,   MEM_READ_ABSOLUTE_X,    3,     4,      1]
opcode_table[0x59] = [eorMem_,   MEM_READ_ABSOLUTE_Y,    3,     4,      1]
opcode_table[0x41] = [eorMem_,   MEM_READ_INDIRECT_X,    2,     6,      0]
opcode_table[0x51] = [eorMem_,   MEM_READ_INDIRECT_Y,    2,     5,      1]

# INC
opcode_table[0xe6] = [incMem_,   MEM_READ_ZEROPAGE,       2,     5,      0]
opcode_table[0xf6] = [incMem_,   MEM_READ_ZEROPAGE_X,     2,     6,      0]
opcode_table[0xee] = [incMem_,   MEM_READ_ABSOLUTE,       3,     6,      0]
opcode_table[0xfe] = [incMem_,   MEM_READ_ABSOLUTE_X,     3,     7,      0]

# INX
opcode_table[0xe8] = [inx_,      MEM_READ_ZEROPAGE,       1,     2,      0]

# INY
opcode_table[0xc8] = [iny_,      MEM_READ_ZEROPAGE,       1,     2,      0]

# JMP
opcode_table[0x4c] = [jmp_,      MEM_READ_ABSOLUTE,       3,     3,      0]
opcode_table[0x6c] = [jmp_,      MEM_READ_INDIRECT,       3,     5,      0]

# JSR
opcode_table[0x20] = [jsr_,      MEM_READ_ABSOLUTE,       3,     6,      0]

# LDA
opcode_table[0xa9] = [lda_,      IMMEDIATE,               2,     2,      0]
opcode_table[0xa5] = [ldaMem_,   MEM_READ_ZEROPAGE,       2,     3,      0]
opcode_table[0xb5] = [ldaMem_,   MEM_READ_ZEROPAGE_X,     2,     4,      0]
opcode_table[0xad] = [ldaMem_,   MEM_READ_ABSOLUTE,       3,     4,      0]
opcode_table[0xbd] = [ldaMem_,   MEM_READ_ABSOLUTE_X,     3,     4,      1]
opcode_table[0xb9] = [ldaMem_,   MEM_READ_ABSOLUTE_Y,     3,     4,      1]
opcode_table[0xa1] = [ldaMem_,   MEM_READ_INDIRECT_X,     2,     6,      0]
opcode_table[0xb1] = [ldaMem_,   MEM_READ_INDIRECT_Y,     2,     5,      1]

# LDX
opcode_table[0xa2] = [ldx_,      IMMEDIATE,               2,     2,      0]
opcode_table[0xa6] = [ldxMem_,   MEM_READ_ZEROPAGE,       2,     3,      0]
opcode_table[0xb6] = [ldxMem_,   MEM_READ_ZEROPAGE_Y,     2,     4,      0]
opcode_table[0xa3] = [ldxMem_,   MEM_READ_ABSOLUTE,       3,     4,      0]
opcode_table[0xbe] = [ldxMem_,   MEM_READ_ABSOLUTE_Y,     3,     4,      1]

# LDY
opcode_table[0xa0] = [ldy_,      IMMEDIATE,               2,     2,      0]
opcode_table[0xa4] = [ldyMem_,   MEM_READ_ZEROPAGE,       2,     3,      0]
opcode_table[0xb4] = [ldyMem_,   MEM_READ_ZEROPAGE_X,     2,     4,      0]
opcode_table[0xac] = [ldyMem_,   MEM_READ_ABSOLUTE,       3,     4,      0]
opcode_table[0xbc] = [ldyMem_,   MEM_READ_ABSOLUTE_X,     3,     4,      1]

# LSR
opcode_table[0x4a] = [lsrAcc_,   IMMEDIATE,               1,     2,      0]
opcode_table[0x46] = [lsrMem_,   MEM_READ_ZEROPAGE,       2,     5,      0]
opcode_table[0x56] = [lsrMem_,   MEM_READ_ZEROPAGE_X,     2,     6,      0]
opcode_table[0x4e] = [lsrMem_,   MEM_READ_ABSOLUTE,       3,     6,      0]
opcode_table[0x5e] = [lsrMem_,   MEM_READ_ABSOLUTE_X,     3,     7,      0]

# NOP
opcode_table[0xea] = [nop_,      IMMEDIATE,               1,     2,      0]

# ORA
opcode_table[0x09] = [ora_,      IMMEDIATE,               2,     2,      0]
opcode_table[0x05] = [oraMem_,   MEM_READ_ZEROPAGE,       2,     3,      0]
opcode_table[0x15] = [oraMem_,   MEM_READ_ZEROPAGE_X,     2,     4,      0]
opcode_table[0x0d] = [oraMem_,   MEM_READ_ABSOLUTE,       3,     4,      0]
opcode_table[0x1d] = [oraMem_,   MEM_READ_ABSOLUTE_X,     3,     4,      1]
opcode_table[0x19] = [oraMem_,   MEM_READ_ABSOLUTE_Y,     3,     4,      1]
opcode_table[0x01] = [oraMem_,   MEM_READ_INDIRECT_X,     2,     6,      0]
opcode_table[0x11] = [oraMem_,   MEM_READ_INDIRECT_Y,     2,     5,      1]

# PHA
opcode_table[0x48] = [pha_,      IMMEDIATE,               1,     3,      0]

# PHP
opcode_table[0x08] = [php_,      IMMEDIATE,               1,     3,      0]

# PLA
opcode_table[0x68] = [pla_,      IMMEDIATE,               1,     4,      0]

# PLP
opcode_table[0x28] = [plp_,      IMMEDIATE,               1,     4,      0]

# ROL
opcode_table[0x2a] = [rolAcc_,   IMMEDIATE,               1,     2,      0]
opcode_table[0x26] = [rolMem_,   MEM_READ_ZEROPAGE,       2,     5,      0]
opcode_table[0x36] = [rolMem_,   MEM_READ_ZEROPAGE_X,     2,     6,      0]
opcode_table[0x2e] = [rolMem_,   MEM_READ_ABSOLUTE,       3,     6,      0]
opcode_table[0x3e] = [rolMem_,   MEM_READ_ABSOLUTE_X,     3,     7,      0]

# ROR                                                 
opcode_table[0x6a] = [rorAcc_,   IMMEDIATE,               1,     2,      0]
opcode_table[0x66] = [rorMem_,   MEM_READ_ZEROPAGE,       2,     5,      0]
opcode_table[0x76] = [rorMem_,   MEM_READ_ZEROPAGE_X,     2,     6,      0]
opcode_table[0x6e] = [rorMem_,   MEM_READ_ABSOLUTE,       3,     6,      0]
opcode_table[0x7e] = [rorMem_,   MEM_READ_ABSOLUTE_X,     3,     7,      0]

#TODO: Voy por aqui
# RTI                                                
opcode_table[0x40] = [pla_, IMMEDIATE,               1,     6,      0]

# RTS                                                
opcode_table[0x60] = [plp_, IMMEDIATE,               1,     6,      0]

# SBC                                                
opcode_table[0x09] = [sbc_, IMMEDIATE,               2,     2,      0]
opcode_table[0x05] = [sbc_, MEM_READ_ZEROPAGE,       2,     3,      0]
opcode_table[0x15] = [sbc_, MEM_READ_ZEROPAGE_X,     2,     4,      0]
opcode_table[0x0d] = [sbc_, MEM_READ_ABSOLUTE,       3,     4,      0]
opcode_table[0x1d] = [sbc_, MEM_READ_ABSOLUTE_X,     3,     4,      0]
opcode_table[0x19] = [sbc_, MEM_READ_ABSOLUTE_Y,     3,     4,      0]
opcode_table[0x01] = [sbc_, MEM_READ_INDIRECT_X,     2,     6,      0]
opcode_table[0x11] = [sbc_, MEM_READ_INDIRECT_Y,     2,     5,      0]

# SEC
opcode_table[0x38] = [sec_, IMMEDIATE,               1,     2,      0]

# SED                                                
opcode_table[0xf8] = [sed_, IMMEDIATE,               1,     2,      0]

# SEI                                                
opcode_table[0x78] = [sei_, IMMEDIATE,               1,     2,      0]

# STA                                                
opcode_table[0x85] = [staZP_,   IMMEDIATE,           2,     3,      0]
opcode_table[0x95] = [staZPX_,  IMMEDIATE,           2,     4,      0]
opcode_table[0x8d] = [staABS_,  IMMEDIATE,           3,     4,      0]
opcode_table[0x9d] = [staABSX_, IMMEDIATE,           3,     5,      0]
opcode_table[0x00] = [staABSY_, IMMEDIATE,           3,     5,      0]
opcode_table[0x81] = [staINDX_, IMMEDIATE,           2,     6,      0]
opcode_table[0x91] = [staINDY_, IMMEDIATE,           2,     6,      0]

# STX                                                
opcode_table[0x86] = [stxZP_,   IMMEDIATE,           2,     3,      0]
opcode_table[0x96] = [stxZPY_,  IMMEDIATE,           2,     4,      0]
opcode_table[0x8e] = [stxABS_,  IMMEDIATE,           3,     4,      0]

# STY                                                
opcode_table[0x84] = [styZP_,   IMMEDIATE,           2,     3,      0]
opcode_table[0x94] = [styZPX_,  IMMEDIATE,           2,     4,      0]
opcode_table[0x8c] = [styABS_,  IMMEDIATE,           3,     4,      0]

# TAX                                                
opcode_table[0xaa] = [tax_,   NONE,                  1,     2,      0]

# TAY                                                
opcode_table[0xaa] = [tay_,   NONE,                  1,     2,      0]

# TSX                                                
opcode_table[0xba] = [tsx_,   NONE,                  1,     2,      0]

# TSA                                                
opcode_table[0x8a] = [tsa_,   NONE,                  1,     2,      0]

# TXS                                                
opcode_table[0x9a] = [txs_,   NONE,                  1,     2,      0]

# TYA                                                
opcode_table[0x98] = [tya_,   NONE,                  1,     2,      0]


def draw_line():
    '''
    Instead of updating display in real time, we'll keep track of any operation
    done over TIA registers and then we'll update the whole line at once
    '''
    
    line_visible = line - 40
    
    # Update background
    s2 = colubk[0][0]
    for i in range(len(colubk) - 1):
        s1 = s2
        s2 = colubk[i+1][0]
        color = colorMap[colubk[i][1]>>1]
        screen[s1:s2, line_visible] = color
    color = colorMap[(colubk[-1][1]>>1)]
    screen[s2:160, line_visible] = color
    
    # Priority depends on CTRLPF.D2: assume it is 0 at this moment
    # PF color depends on CTRLPF D1: assume it is 0 at this moment (so use COLUPF)
    # PF reflection depends on CTRLPF D0: assume it is 0 at this moment (so no mirror)
    
    # Update PlayFields
    # Simplification: assume color changes, at most, once each line 
    if memory[CTRLPF] & 0x02:
        PF_color1 = colorMap[memory[COLUP0]>>1]
        PF_color2 = colorMap[memory[COLUP1]>>1]
    else:
        PF_color1 = colorMap[memory[COLUPF]>>1]
        PF_color2 = PF_color1

    a1 = time.clock()

    # left-side display
    if pf0_1 & 0x10: 
        screen[0:4, line_visible]   = PF_color1
    if pf0_1 & 0x20: 
        screen[4:8, line_visible]   = PF_color1
    if pf0_1 & 0x40: 
        screen[8:12, line_visible]  = PF_color1
    if pf0_1 & 0x80: 
        screen[12:16, line_visible] = PF_color1
    if pf1_1 & 0x80:
        screen[16:20, line_visible] = PF_color1
    if pf1_1 & 0x40:
        screen[20:24, line_visible] = PF_color1
    if pf1_1 & 0x20:
        screen[24:28, line_visible] = PF_color1
    if pf1_1 & 0x10:
        screen[28:32, line_visible] = PF_color1
    if pf1_1 & 0x08:
        screen[32:36, line_visible] = PF_color1
    if pf1_1 & 0x04:
        screen[36:40, line_visible] = PF_color1
    if pf1_1 & 0x02:
        screen[40:44, line_visible] = PF_color1
    if pf1_1 & 0x01:
        screen[44:48, line_visible] = PF_color1
    if pf2_1 & 0x01:
        screen[48:52, line_visible] = PF_color1
    if pf2_1 & 0x02:
        screen[52:56, line_visible] = PF_color1
    if pf2_1 & 0x04:
        screen[56:60, line_visible] = PF_color1
    if pf2_1 & 0x08:
        screen[60:64, line_visible] = PF_color1
    if pf2_1 & 0x10:
        screen[64:68, line_visible] = PF_color1
    if pf2_1 & 0x20:
        screen[68:72, line_visible] = PF_color1
    if pf2_1 & 0x40:
        screen[72:76, line_visible] = PF_color1
    if pf2_1 & 0x80:
        screen[76:80, line_visible]= PF_color1

    # right-side
    if not pf_mirror:
        if pf0_2 & 0x10: 
            screen[80:84, line_visible]   = PF_color2
        if pf0_2 & 0x20: 
            screen[84:88, line_visible]   = PF_color2
        if pf0_2 & 0x40: 
            screen[88:92, line_visible]   = PF_color2
        if pf0_2 & 0x80: 
            screen[92:96, line_visible]   = PF_color2
        if pf1_2 & 0x80: 
            screen[96:100, line_visible]  = PF_color2
        if pf1_2 & 0x40: 
            screen[100:104, line_visible] = PF_color2
        if pf1_2 & 0x20: 
            screen[104:108, line_visible] = PF_color2
        if pf1_2 & 0x10: 
            screen[108:112, line_visible] = PF_color2
        if pf1_2 & 0x08: 
            screen[112:116, line_visible] = PF_color2
        if pf1_2 & 0x04: 
            screen[116:120, line_visible] = PF_color2
        if pf1_2 & 0x02: 
            screen[120:124, line_visible] = PF_color2
        if pf1_2 & 0x01: 
            screen[124:128, line_visible] = PF_color2
        if pf2_2 & 0x01: 
            screen[128:132, line_visible] = PF_color2
        if pf2_2 & 0x02: 
            screen[132:136, line_visible] = PF_color2
        if pf2_2 & 0x04: 
            screen[136:140, line_visible] = PF_color2
        if pf2_2 & 0x08: 
            screen[140:144, line_visible] = PF_color2
        if pf2_2 & 0x10: 
            screen[144:148, line_visible] = PF_color2
        if pf2_2 & 0x20: 
            screen[148:152, line_visible] = PF_color2
        if pf2_2 & 0x40: 
            screen[152:156, line_visible] = PF_color2
        if pf2_2 & 0x80: 
            screen[156:160, line_visible] = PF_color2
    else:
        if pf2_2 & 0x80: 
            screen[80:84, line_visible]   = PF_color2
        if pf2_2 & 0x40: 
            screen[84:88, line_visible]   = PF_color2
        if pf2_2 & 0x20: 
            screen[88:92, line_visible]   = PF_color2
        if pf2_2 & 0x10: 
            screen[92:96, line_visible]   = PF_color2
        if pf2_2 & 0x08: 
            screen[96:100, line_visible]  = PF_color2
        if pf2_2 & 0x04: 
            screen[100:104, line_visible] = PF_color2
        if pf2_2 & 0x02: 
            screen[104:108, line_visible] = PF_color2
        if pf2_2 & 0x01: 
            screen[108:112, line_visible] = PF_color2
        if pf1_2 & 0x01: 
            screen[112:116, line_visible] = PF_color2
        if pf1_2 & 0x02: 
            screen[116:120, line_visible] = PF_color2
        if pf1_2 & 0x04: 
            screen[120:124, line_visible] = PF_color2
        if pf1_2 & 0x08: 
            screen[124:128, line_visible] = PF_color2
        if pf1_2 & 0x10: 
            screen[128:132, line_visible] = PF_color2
        if pf1_2 & 0x20: 
            screen[132:136, line_visible] = PF_color2
        if pf1_2 & 0x40: 
            screen[136:140, line_visible] = PF_color2
        if pf1_2 & 0x80: 
            screen[140:144, line_visible] = PF_color2
        if pf0_2 & 0x80: 
            screen[144:148, line_visible] = PF_color2
        if pf0_2 & 0x40: 
            screen[148:152, line_visible] = PF_color2
        if pf0_2 & 0x20: 
            screen[152:156, line_visible] = PF_color2
        if pf0_2 & 0x10: 
            screen[156:160, line_visible] = PF_color2
    #k=0
    #for j in range(8):
    #    if pf0_1 & (0x10<<j) and j < 4: 
    #        screen[k:k+4, line_visible]     = PF_color1
    #    if pf1_1 & (0x80>>j): 
    #        screen[k+16:k+20, line_visible] = PF_color1
    #    if pf2_1 & (0x01<<j): 
    #        screen[k+48:k+52, line_visible] = PF_color1
    #    if not pf_mirror:
    #        if pf0_2 & (0x10<<j) and j < 4: 
    #            screen[k+80:k+84, line_visible]   = PF_color2 # Assuming no mirror
    #        if pf1_2 & (0x80>>j): 
    #            screen[k+96:k+100, line_visible]  = PF_color2
    #        if pf2_2 & (0x01<<j): 
    #            screen[k+128:k+132, line_visible] = PF_color2
    #    else:
    #        if pf2_2 & (0x80>>j): 
    #            screen[k+80:k+84, line_visible]   = PF_color2 # Assuming mirror
    #        if pf1_2 & (0x01<<j): 
    #            screen[k+112:k+116, line_visible] = PF_color2
    #        if pf0_2 & (0x80>>j) and j < 4: 
    #            screen[k+144:k+148, line_visible] = PF_color2 # Assuming no mirror
    #    k += 4

    a2 = time.clock()
    #print(a2-a1)
#
#    # Update Ball
#    screen[BALL_pos, line] = BALL_color # Assuming one pixel size
#
    # Update GPs and missiles
    size = 1
    P0_color = colorMap[memory[COLUP0]>>1] # assuming no change in color during the first half-line
    P1_color = colorMap[memory[COLUP1]>>1] # idem for second half-line
    for i in range(8):
        if memory[GRP0] & (0x80>>i):
            screen[P0_pos + i:P0_pos + i + 1, line - 40] = P0_color # Assuming one pixel size
        if memory[GRP1] & (0x80>>i):
            screen[P1_pos + i:P1_pos + i + 1, line - 40] = P1_color # Assuming one pixel size
        #screen[GP1_pos + i, line - 40] = GP1_color
        #screen[MP1_pos + i, line - 40] = GP1_color




import time


#f = open("Indy500.a26", "rb")
#f = open("3_Bars_Background.bin", "rb")
#with open("prueba.bin", "rb") as f:
with open("kernel_13.bin", "rb") as f:
    rom = f.read()

for i, byte in enumerate(rom):
    memory[0x1000 + i] = ord(byte)

pygame.init()
display = pygame.display.set_mode([160,192], flags = pygame.SCALED)

PC = 0x1000
ss = 0
t1 = time.time()
#for i in range(1100):
for i in range(1900*401):
    page_crossed = 0
    
    # Get the next opcode
    opcode = memory[PC]
    #print hex(opcode)
    opFunc, opMode, nbytes, ncycles, add_page_crossed = opcode_table[opcode]
    
    # Get the operand (if appropriate)
    if nbytes == 2  : addr = opMode(memory[PC+1])
    elif nbytes == 3: addr = opMode(memory[PC+1] + (memory[PC+2]<<8))
    else            : addr = 0

    # Update PC
    PC = (PC + nbytes) & MAX_MEM_ADDR

    #print hex(PC), hex(opcode), opFunc, addr, nbytes, ncycles
    # Execute opcode
    extra_cycles  = opFunc(addr)
    extra_cycles += add_page_crossed * page_crossed

    # Update num cycles
    num_cycles = num_cycles + (ncycles + extra_cycles) * 3

    # TIA: Register update
    if TIA_UPDATE:
        TIA_UPDATE = False
        TIA_update()
    
    # TIA: draw TV line
    if num_cycles >= 228:
        num_cycles %= 228
        #print num_cycles % 228
        #num_cycles = 0
        
        if line >= 40 and line < 232:
            draw_line()
        colubk = [[0, memory[COLUBK] ]]
        pf0_1 = pf0_2 = memory[PF0]
        pf1_1 = pf1_2 = memory[PF1]
        pf2_1 = pf2_2 = memory[PF2]
        tmp   = memory[CTRLPF]
        pf_mirror = 1 if tmp & 0x01 else 0
        line += 1
        if line >= 262:
            t2 = time.time()
            print 1/(t2-t1), ' Hz'
            t1 = t2
            line = 0
            ss +=1
            ss = 0
            if ss%20 == 0:
                pass
                pygame.surfarray.blit_array(display, screen)
                pygame.display.update()


#
# TIA
#
# Each TV line is updated at once when the line ends (probably at STA WSYNC instruction)
# Assume:
# - Background does not change during the line -> all line same color
# - Playfield can only change before each mid-line -> can be different for each midline -> store 1st midline as PFx_first
# - Each TRIGGER register (GP, missile, ball) is written 0 or 1 time a line -> Store at which pixel were triggered each one
#
# So, ... (draw all objects layer by layer. Order depends on some registers)
# - First, fill the whole line with the BG color
# - Second, draw the two Playfields
# - Third,  draw the ball
# - Fourth, draw GP0 and missile 0
# - Fourth, draw GP1 and missile 1
# - Reset tbe number of cycles at the end of each line. Assuming NTSC:
# First mid-line starts at cycle 68 and the second one at 148. HSYNC is at 228.
#

#    
#
#last_cycle = 0
#def TIA():
#    # Trigger registers
#    # Can be any value (but always 8-bit, so never 0xffff)
#    if memory[WSYNC] != 0xffff:    # Trigger WSYNC
#        memory[WSYNC] = 0xffff
#        cycle = 228  # CPU halted until the TV line end
#
#    if memory[HMOVE] != 0xffff:
#        memory[HMOVE] = 0xffff
#        P0_pos += memory[HMP0] # TODO: -8 to +7
#        P1_pos += memory[HMP1]
#        M0_pos += memory[HMM0]
#        M1_pos += memory[HMM1]
#        BL_pos += memory[HMBL]
#
#    if memory[HMCLR] != 0xffff:
#        memory[HMCLR] = 0xffff
#        HMP0 = HMP1 = HMM0 = HMM1 = HMBL = 0
#
#    if memory[CXCLR] != 0xffff:
#        pass

#
#    if cycle >= 228:
#        cycle = 0
#        draw_line()
#    else:
#        if TRIGGER_GP0: GP0_pos = cycles
#        if TRIGGER_GP1: GP1_pos = cycles
#        if TRIGGER_MP0: MP0_pos = cycles
#        if TRIGGER_MP1: MP1_pos = cycles
#        if TRIGGER_BALL: BALL_pos = cycles
#        if HMOV: update ALL xxx_pos values
#
#    last_cycle = cycle

#




