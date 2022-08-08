# No BCD implementation
# Only NTSC
# REMIND!!! TIA 0x00-0x0D registers RD and WR are NOT the same!!! same address, but different registers
# Add Remapping (ie: TIA 0x40 is 0x00). Advice: 64byte blocks
# Set default value for input registers

import numpy as np
import pygame

import time
import sys
import code
from tia import TIA
from cpu import cpu

class System:
    def __init__(self):
        self.clk_cycles = 0
        self.memory = [0 for x in range(2**13)]

    def dump(self):
        print("\nSYSTEM\n")
        print("clk_cycles {}\n".format(self.clk_cycles))
        print("Memory\n")
        print("TBD\n")
        #for i in range(0,0x2C, 0x10):
        #    print(("{:02X} "*0x10).format(*memory[i:i+0x10]))



#def memoryMap(addr):
#    ''' There are mirrors for several memory areas
#        I.e.: 8K (max adderesable space) mirrored at 0x0000, 0x2000, ..., 0xE000
#
#        ROM:   xxx1 NNNN NNNN NNNN
#               Mirrors: 0x1000, 0x3000, ..., 0xF000
#
#        TIA:   xxx0 xxxx 0xNN NNNN
#               MIrrors: 0x0000, 0x0040, 0x0100, 0x0140, ..., 0x0F00, 0x0F40
#                  14 read-only registers mirrored 4 times inside each 64 address space
#                  45 write-only registers
#
#        RIOT:  xxx0 xxMx 1NNN NNNN
#               M is mode (0: RAM, 1: I/O+Timer)
#               Mirrors: RAM: 0x0080, 0x0180, 0x0480, 0x0580, ..., 0x0C80, 0x0D80
#                        I/O: 0x0280, 0x0380, 0x0680, 0x0780, ..., 0x0E80, 0x0F80
#    ''' 
#
#    if addr & 0x1000:
#        # ROM: 0x1000 - 0x1FFF
#        physical_addr = addr & 0x1FFF
#    else:
#        if addr & 0x80:
#            # RIOT address space
#            if addr & 0x200:
#                # IO: 0x280 - 0x2FF
#                physical_addr = addr & 0x02FF
#            else:
#                # RAM: 0x80 - 0xFF
#                physical_addr = addr & 0x00FF
#        else:
#            # TIA address space: 0x00 - 0x3F
#            physical_addr = addr & 0x003F
#
#    return physical_addr


def print_debug(text):
    pass
    #print(text)

#
# ATARI 2600 core
#

A = X = Y = 0                      # Registers
PC = 0                             # Program counter
SP = 0                             # Stack pointer
N = V = B = D = I = Z = C = False  # Status flags

page_crossed = 0
frame_cnt = 0
total_cycles = 0
##
TIA_UPDATE = False
tia_addr  = 0
tia_value = 0
#
##RIOT (PIA 6532)
RIOT_UPDATE = False
riot_addr  = 0
riot_value = 0
tim_prescaler = 1024 # default value
tim_cnt       = 15   # default value
#
#
MAX_MEM_ADDR = 0x1fff # 8KB-1 (13-bits)
#
#

# NEWWWW
system = System()
tia = TIA(system)
#END NEW

def RIOT_update():
    global system
    global tim_cnt,tim_prescaler
    
    addr  = riot_addr
    value = riot_value

    # Trigger registers (ignore value)
    if addr == 0x294:
        system.memory[0x284] = value
        tim_prescaler =1 
        tim_cnt = 1
        print_debug("TIMER 1: {}, clk_cycles: {}".format(value, system.clk_cycles/3))
    elif addr == 0x295:
        system.memory[0x284] = value
        tim_prescaler =8 
        tim_cnt = 1
        print_debug("TIMER 8: {}, clk_cycles: {}".format(value, system.clk_cycles/3))
    elif addr == 0x296:
        system.memory[0x284] = value
        tim_prescaler = 64
        tim_cnt = 1
        print_debug("TIMER 64: {}, clk_cycles: {}".format(value, system.clk_cycles/3))
    elif addr == 0x297:
        system.memory[0x284] = value
        tim_prescaler =1024 
        tim_cnt = 1
        print_debug("TIMER 1024: {}, clk_cycles: {}".format(value, system.clk_cycles/3))

    # elif ...


# Memory bus operation
def MEM_WRITE(addr, value):
    global system
    #global memory
    global mem_write

    mem_write = 1

    addr &= MAX_MEM_ADDR

    if addr >= 0x40 and addr < 0x80:
        print_debug("ZERO PAGE 0x{:02X}".format(addr))
        addr -= 0x40
        #sys.exit()

    if addr != 0x282: # Port B is hardwired as input. Ignore write operations on it
        system.memory[addr] = value
    
    #if addr > 0x30 and addr < 0x3f:
    #    print( 'WTF' )
    #    #sys.exit()

    # TIA register (0x00 - 0x80)
    if addr < 0x80:
        global TIA_UPDATE, tia_addr, tia_value
        TIA_UPDATE = True
        tia_addr  = addr
        tia_value = value

        if addr > 0x3f:
            print_debug('W_ADDR {}'.format(hex(addr)))

    if addr >= 0x280:
        global RIOT_UPDATE, riot_addr, riot_value
        RIOT_UPDATE = True
        riot_addr  = addr
        riot_value = value
        print_debug('W_ADDR 0x{:4X}, val:{}'.format(addr, value))

            
def MEM_READ(addr):

    global mem_read

    mem_read = 1

    addr &= MAX_MEM_ADDR

    if addr >= 0x40 and addr < 0x80:
        print_debug("ZERO PAGE {}".format(addr))
        addr -= 0x40
        sys.exit()

    if addr > 0x280 and addr < 0x300:
        print_debug("R_ADDR {} PC:{}, tim_pres:{}, tim_cnt:{}".format(hex(addr), hex(PC), tim_prescaler, tim_cnt))

    if addr < 0x0E or (addr >= 0x30 and addr < 0x3E):
        addr = (addr & 0x0F) + 0x100 # fake address for read-only TIA registers
    #    return tia_rd[addr & 0x0F]

    return system.memory[addr]




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
    return addr & 0xff

def MEM_READ_ZEROPAGE_X(addr):
    return (addr + X) & 0xff

def MEM_READ_ZEROPAGE_Y(addr):
    return (addr + Y) & 0xff

def MEM_READ_ABSOLUTE(addr):

    return addr

# Not clear the 'page_crossed' extra cycle: https://wiki.nesdev.com/w/index.php/CPU_addressing_modes
def MEM_READ_ABSOLUTE_X(addr):
    global page_crossed

    addr = addr + X
    if (addr & 0xff) < X: page_crossed = 1
    return addr

def MEM_READ_ABSOLUTE_Y(addr):
    global page_crossed

    addr = addr + Y
    if (addr & 0xff) < Y: page_crossed = 1
    return addr

def MEM_READ_INDIRECT(addrL):
    # HW Bug in original 6502 processor (instead of addrH = addrL+1)
    addrH = (addrL & 0xff00) | ((addrL + 1) & 0x00ff)
    addr = MEM_READ(addrL) | (MEM_READ(addrH)<<8)

    return addr

def MEM_READ_INDIRECT_X(addr):
    addr = (addr + X) & 0xff
    addr = MEM_READ(addr) | (MEM_READ((addr + 1) & 0xff) << 8)
    return addr

def MEM_READ_INDIRECT_Y(addr):
    global page_crossed
    
    addr = MEM_READ(addr) | (MEM_READ((addr + 1) & 0xff) << 8)
    addr = addr + Y
    if (addr & 0xff) < Y: page_crossed = 1
    return addr

#TODO: maybe delete this macros
# WRITE
def MEM_WRITE_ZEROPAGE(addr, val):
    MEM_WRITE(addr & 0xff, val)

def MEM_WRITE_ZEROPAGE_X(addr, val):
    MEM_WRITE((addr +  X) & 0xff, val)
#
def MEM_WRITE_ZEROPAGE_Y(addr, val):
    MEM_WRITE((addr +  Y) & 0xff, val)

def MEM_WRITE_ABSOLUTE(addr, val):
    MEM_WRITE(addr, val)

def MEM_WRITE_ABSOLUTE_X(addr, val):
    MEM_WRITE((addr + X), val)    

def MEM_WRITE_ABSOLUTE_Y(addr, val):
    MEM_WRITE((addr + Y), val)    
    
#def MEM_WRITE_MEM_READ_INDIRECT(addr, val):
#    addr = memory[addr] | memory[addr + 1]<<8
#    MEM_WRITE(addr & MAX_MEM_ADDR, val)
    
def MEM_WRITE_INDIRECT_X(addr, val):
    addr = (addr+ X) & 0xff
    addr = MEM_READ(addr) | (MEM_READ(addr+1)<<8)
    MEM_WRITE(addr, val)

def MEM_WRITE_INDIRECT_Y(addr, val):
    addr = MEM_READ(addr) | (MEM_READ(addr+1)<<8)
    addr = addr + Y
    MEM_WRITE(addr, val)

# END Addressing modes

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
    print("opcode not implemented")
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
    return and_(MEM_READ(addr))

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
    global system
    #global memory
    global PC, SP
    global B

    B = 1
    # push PC and SP to stack
    rti_PC = PC + 1
    system.memory[SP]     = rti_PC >> 8
    system.memory[SP - 1] = rti_PC & 0xff
    system.memory[SP - 2] = PSW_GET()
    SP -= 3
    # PC = interrupt vector
    PC = (MEM_READ(MEM_READ_ABSOLUTE(0xfffe)) | MEM_READ(MEM_READ_ABSOLUTE(0xffff))<<8)
    print_debug(hex(PC))

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

    return 0

def eorMem_(addr):
    global A

    val = MEM_READ(addr)
    A ^= val
    Z = A == 0
    N = (A & 0x80) != 0

    return 0

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
    
    PC = val

    return 0
    
# JSR
def jsr_(val):
    global PC, SP
    global system
    #global memory
    #print(hex(val & MAX_MEM_ADDR))
    # push PC-1 on to the stack
    PC -= 1
    system.memory[SP]     = PC >> 8
    system.memory[SP - 1] = PC & 0xff
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
    global A
    global Z, N, C
    
    C = (A & 0x01) != 0
    A = A >> 1
    Z = (A == 0)
    N = (A & 0x80) != 0
    
    return 0

def lsrMem_(addr):
    global Z, N, C
    
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
    global system
    #global memory

    system.memory[SP] = A
    SP = SP - 1

    return 0    

def php_(val):
    global SP
    global system
    #global memory

    system.memory[SP] = PSW_GET()
    SP = SP - 1

    return 0    

def pla_(val):
    global A, SP
    global Z, N

    SP = SP + 1
    A = system.memory[SP]
    Z = A == 0 
    N = (A & 0x80 != 0) 

    return 0

def plp_(val):
    global SP
    global C,Z,I,D,B,V,N

    SP = SP + 1
    tmp = system.memory[SP]
    PSW_SET(tmp)

    return 0

# ROL
def rol_(val):
    global A
    global Z,N,C

    res = (A << 1) | C # Mixing integer and boolean, but it is OK (True -> 1)
    A = res & 0xff
    C = res > 0xff
    Z = (A == 0)
    N = (A & 0x80) != 0    

    return 0

def rolMem_(addr):
    global Z,N,C

    res = (MEM_READ(addr) << 1) | C
    val = res & 0xff
    MEM_WRITE(addr, val)
    C = res > 0xff
    Z = (val == 0)
    N = (val & 0x80) != 0    

    return 0

# ROR
def ror_(val):
    global A
    global Z,C,N
    
    bit0 = val & 0x01
    A = (val >> 1) | (C << 7) # Mixing integer and boolean, but it is OK (True -> 1)
    N = C
    C = (bit0 != 0)
    Z = (A == 0)
    
    return 0

def rorMem_(addr):
    global Z,C,N
    
    val = MEM_READ(addr)
    bit0 = val & 0x01
    res = (val >> 1) | (C << 7)
    MEM_WRITE(addr, res)
    N = C
    C = (bit0 != 0)
    Z = (res == 0)
    
    return 0


# RTI
def rti_(unused):
    global PC, SP
    global C,Z,I,D,B,V,N

    PSW_SET(system.memory[SP + 1])
    PC = system.memory[SP + 2] | (system.memory[SP + 3] << 8)
    SP += 3

    return 0

# RTS
def rts_(unused):
    global PC, SP

    PC = (system.memory[SP + 1] | (system.memory[SP + 2] << 8)) + 1
    SP += 2

    return 0

# SBC (DMG: BCD mode not implemented)
def sbc_(val):
    return adc_(val ^ 0xff)
    #global A
    #global Z,C,V,N

    #res = A - val - (C - 1)
    #
    #A = res & 0xff
    #Z = A == 0
    ##C = ?
    ##V = ?
    #N = (A & 0x80) != 0

    #return page_crossed

def sbcMem_(addr_):
    return sbc_(MEM_READ(addr))

# SEC
def sec_(unused):
    global C

    C = 1

    return 0

# SED
def sed_(unused):
    global D

    D = 1

    return 0    

# SEI
def sei_(unused):
    global I

    I = 1

    return 0

# STA
def staMem_(addr):

    MEM_WRITE(addr, A)

    return 0

# STX
def stxMem_(addr):

    MEM_WRITE(addr, X)

    return 0

# STY
def styMem_(addr):

    MEM_WRITE(addr, Y)

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

# End pcode


# opcodes table
opcode_table = [[unknown, IMMEDIATE, 0, 0, 0] for x in range(256)]
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
opcode_table[0x24] = [bit_,      MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0x2c] = [bit_,      MEM_READ_ABSOLUTE,     3,     4,      0]

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
opcode_table[0xdd] = [cmpMem_,   MEM_READ_ABSOLUTE_X,   3,     4,      1]
opcode_table[0xd9] = [cmpMem_,   MEM_READ_ABSOLUTE_Y,   3,     4,      1]
opcode_table[0xc1] = [cmpMem_,   MEM_READ_INDIRECT_X,   2,     6,      0]
opcode_table[0xd1] = [cmpMem_,   MEM_READ_INDIRECT_Y,   2,     5,      1]

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
opcode_table[0x49] = [eor_,      IMMEDIATE,             2,     2,      0]
opcode_table[0x45] = [eorMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0x55] = [eorMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0x4d] = [eorMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0x5d] = [eorMem_,   MEM_READ_ABSOLUTE_X,   3,     4,      1]
opcode_table[0x59] = [eorMem_,   MEM_READ_ABSOLUTE_Y,   3,     4,      1]
opcode_table[0x41] = [eorMem_,   MEM_READ_INDIRECT_X,   2,     6,      0]
opcode_table[0x51] = [eorMem_,   MEM_READ_INDIRECT_Y,   2,     5,      1]

# INC
opcode_table[0xe6] = [incMem_,   MEM_READ_ZEROPAGE,     2,     5,      0]
opcode_table[0xf6] = [incMem_,   MEM_READ_ZEROPAGE_X,   2,     6,      0]
opcode_table[0xee] = [incMem_,   MEM_READ_ABSOLUTE,     3,     6,      0]
opcode_table[0xfe] = [incMem_,   MEM_READ_ABSOLUTE_X,   3,     7,      0]

# INX
opcode_table[0xe8] = [inx_,      MEM_READ_ZEROPAGE,     1,     2,      0]

# INY
opcode_table[0xc8] = [iny_,      MEM_READ_ZEROPAGE,     1,     2,      0]

# JMP
opcode_table[0x4c] = [jmp_,      MEM_READ_ABSOLUTE,     3,     3,      0]
opcode_table[0x6c] = [jmp_,      MEM_READ_INDIRECT,     3,     5,      0]

# JSR
opcode_table[0x20] = [jsr_,      MEM_READ_ABSOLUTE,     3,     6,      0]

# LDA
opcode_table[0xa9] = [lda_,      IMMEDIATE,             2,     2,      0]
opcode_table[0xa5] = [ldaMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0xb5] = [ldaMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0xad] = [ldaMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0xbd] = [ldaMem_,   MEM_READ_ABSOLUTE_X,   3,     4,      1]
opcode_table[0xb9] = [ldaMem_,   MEM_READ_ABSOLUTE_Y,   3,     4,      1]
opcode_table[0xa1] = [ldaMem_,   MEM_READ_INDIRECT_X,   2,     6,      0]
opcode_table[0xb1] = [ldaMem_,   MEM_READ_INDIRECT_Y,   2,     5,      1]

# LDX
opcode_table[0xa2] = [ldx_,      IMMEDIATE,             2,     2,      0]
opcode_table[0xa6] = [ldxMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0xb6] = [ldxMem_,   MEM_READ_ZEROPAGE_Y,   2,     4,      0]
opcode_table[0xae] = [ldxMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0xbe] = [ldxMem_,   MEM_READ_ABSOLUTE_Y,   3,     4,      1]

# LDY
opcode_table[0xa0] = [ldy_,      IMMEDIATE,             2,     2,      0]
opcode_table[0xa4] = [ldyMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0xb4] = [ldyMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0xac] = [ldyMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0xbc] = [ldyMem_,   MEM_READ_ABSOLUTE_X,   3,     4,      1]

# LSR
opcode_table[0x4a] = [lsr_,      IMMEDIATE,             1,     2,      0]
opcode_table[0x46] = [lsrMem_,   MEM_READ_ZEROPAGE,     2,     5,      0]
opcode_table[0x56] = [lsrMem_,   MEM_READ_ZEROPAGE_X,   2,     6,      0]
opcode_table[0x4e] = [lsrMem_,   MEM_READ_ABSOLUTE,     3,     6,      0]
opcode_table[0x5e] = [lsrMem_,   MEM_READ_ABSOLUTE_X,   3,     7,      0]

# NOP
opcode_table[0xea] = [nop_,      IMMEDIATE,             1,     2,      0]

# ORA
opcode_table[0x09] = [ora_,      IMMEDIATE,             2,     2,      0]
opcode_table[0x05] = [oraMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0x15] = [oraMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0x0d] = [oraMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0x1d] = [oraMem_,   MEM_READ_ABSOLUTE_X,   3,     4,      1]
opcode_table[0x19] = [oraMem_,   MEM_READ_ABSOLUTE_Y,   3,     4,      1]
opcode_table[0x01] = [oraMem_,   MEM_READ_INDIRECT_X,   2,     6,      0]
opcode_table[0x11] = [oraMem_,   MEM_READ_INDIRECT_Y,   2,     5,      1]

# PHA
opcode_table[0x48] = [pha_,      IMMEDIATE,             1,     3,      0]

# PHP
opcode_table[0x08] = [php_,      IMMEDIATE,             1,     3,      0]

# PLA
opcode_table[0x68] = [pla_,      IMMEDIATE,             1,     4,      0]

# PLP
opcode_table[0x28] = [plp_,      IMMEDIATE,             1,     4,      0]

# ROL
opcode_table[0x2a] = [rol_,      IMMEDIATE,             1,     2,      0]
opcode_table[0x26] = [rolMem_,   MEM_READ_ZEROPAGE,     2,     5,      0]
opcode_table[0x36] = [rolMem_,   MEM_READ_ZEROPAGE_X,   2,     6,      0]
opcode_table[0x2e] = [rolMem_,   MEM_READ_ABSOLUTE,     3,     6,      0]
opcode_table[0x3e] = [rolMem_,   MEM_READ_ABSOLUTE_X,   3,     7,      0]

# ROR                                                 
opcode_table[0x6a] = [ror_,      IMMEDIATE,             1,     2,      0]
opcode_table[0x66] = [rorMem_,   MEM_READ_ZEROPAGE,     2,     5,      0]
opcode_table[0x76] = [rorMem_,   MEM_READ_ZEROPAGE_X,   2,     6,      0]
opcode_table[0x6e] = [rorMem_,   MEM_READ_ABSOLUTE,     3,     6,      0]
opcode_table[0x7e] = [rorMem_,   MEM_READ_ABSOLUTE_X,   3,     7,      0]

#TODO: Voy por aqui
# RTI                                                
opcode_table[0x40] = [rti_,      NONE,                  1,     6,      0]

# RTS                                                         
opcode_table[0x60] = [rts_,      NONE,                  1,     6,      0]

# SBC                                                
opcode_table[0xe9] = [sbc_,      IMMEDIATE,             2,     2,      0]
opcode_table[0xe5] = [sbcMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0xf5] = [sbcMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0xed] = [sbcMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0xfd] = [sbcMem_,   MEM_READ_ABSOLUTE_X,   3,     4,      1]
opcode_table[0xf9] = [sbcMem_,   MEM_READ_ABSOLUTE_Y,   3,     4,      1]
opcode_table[0xe1] = [sbcMem_,   MEM_READ_INDIRECT_X,   2,     6,      0]
opcode_table[0xf1] = [sbcMem_,   MEM_READ_INDIRECT_Y,   2,     5,      1]

# SEC
opcode_table[0x38] = [sec_,      NONE,                  1,     2,      0]

# SED
opcode_table[0xf8] = [sed_,      NONE,                  1,     2,      0]

# SEI
opcode_table[0x78] = [sei_,      NONE,                  1,     2,      0]

# STA                                                
opcode_table[0x85] = [staMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0x95] = [staMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0x8d] = [staMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]
opcode_table[0x9d] = [staMem_,   MEM_READ_ABSOLUTE_X,   3,     5,      0]
opcode_table[0x99] = [staMem_,   MEM_READ_ABSOLUTE_Y,   3,     5,      0]
opcode_table[0x81] = [staMem_,   MEM_READ_INDIRECT_X,   2,     6,      0]
opcode_table[0x91] = [staMem_,   MEM_READ_INDIRECT_Y,   2,     6,      0]

# STX                                                
opcode_table[0x86] = [stxMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0x96] = [stxMem_,   MEM_READ_ZEROPAGE_Y,   2,     4,      0]
opcode_table[0x8e] = [stxMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]

# STY                                                
opcode_table[0x84] = [styMem_,   MEM_READ_ZEROPAGE,     2,     3,      0]
opcode_table[0x94] = [styMem_,   MEM_READ_ZEROPAGE_X,   2,     4,      0]
opcode_table[0x8c] = [styMem_,   MEM_READ_ABSOLUTE,     3,     4,      0]

# TAX                                                
opcode_table[0xaa] = [tax_,      NONE,                  1,     2,      0]

# TAY                                                   
opcode_table[0xa8] = [tay_,      NONE,                  1,     2,      0]

# TSX                                                   
opcode_table[0xba] = [tsx_,      NONE,                  1,     2,      0]

# TSA                                                   
opcode_table[0x8a] = [tsa_,      NONE,                  1,     2,      0]

# TXS                                                   
opcode_table[0x9a] = [txs_,      NONE,                  1,     2,      0]

# TYA                                                   
opcode_table[0x98] = [tya_,      NONE,                  1,     2,      0]

# End opcodes table


cpu = cpu(system)


#f = open("Indy500.a26", "rb")
#f = open("3_Bars_Background.bin", "rb")
#with open("../kernel_01.bin", "rb") as f:
#with open("../ROMS/Space Invaders (1980) (Atari, Richard Maurer - Sears) (CX2632 - 49-75153) ~.bin", "rb") as f:
with open("../prueba.bin", "rb") as f:
    rom = f.read()

for i, byte in enumerate(rom):
    #memory[0x1000 + i] = ord(byte)  # For python2
    #memory[0x1800 + i] = ord(byte)
    system.memory[0x1000 + i] = byte # For python3
    #memory[0x1800 + i] = byte


# Init input registers
system.memory[0x280] = 0xff
system.memory[0x281] = 0x00
system.memory[0x282] = 0x2f
system.memory[0x283] = 0x00 # Actually hardwired as input
system.memory[0x108] = 0x80
system.memory[0x109] = 0x80
system.memory[0x10a] = 0x80
system.memory[0x10b] = 0x80
system.memory[0x10c] = 0x80
system.memory[0x10d] = 0x80

mem_write = 0
mem_read = 0

PC = 0xF000
cpu.PC = 0xF000
ss = 0
t1 = time.time()
#for i in range(1100):
for i in range(19000*401):
#    page_crossed = 0
#
#    mem_write = 0
#    mem_read = 0
#
#    # Get the next opcode
#    print_debug("PC {}".format(hex(PC)))
#    opcode = MEM_READ(PC)
#    #print hex(opcode)
#    opFunc, opMode, nbytes, ncycles, add_page_crossed = opcode_table[opcode]
#    
#    if opFunc == unknown:
#        print("Unknown opcode: {}".format(hex(opcode)))
#        break
#
#    # Get the operand (if appropriate)
#    if nbytes == 2  : addr = opMode(MEM_READ(PC+1))
#    elif nbytes == 3: addr = opMode(MEM_READ(PC+1) + (MEM_READ(PC+2)<<8))
#    else            : addr = 0
#
#    # Update PC
#    PC += nbytes
#
#    # Execute opcode
#    extra_cycles  = opFunc(addr)
#    extra_cycles += add_page_crossed * page_crossed
#
#    # Update num cycles
#    system.clk_cycles = system.clk_cycles + (ncycles + extra_cycles) * 3
#
#    discount = ncycles + extra_cycles

    discount = cpu.execute()

    #TODO not very clear...76-X is always lower than 76, memory[0x284] always decrements 1
    #     This is a TIA registre but affecting CPU execution
##    if wsync:
    if cpu.tia_addr == TIA.WSYNC and cpu.TIA_UPDATE == True:
    #if addr == TIA.WSYNC and mem_write == 1:
        discount = 76 - system.clk_cycles//3
##    else:
##        discount = ncycles + extra_cycles
    if discount > tim_cnt:
        # AND this is RIOT register ... what a mess!
        #memory[0x284] = (memory[0x284] - (discount//76 + 1)) & 0xff
        system.memory[0x284] = (system.memory[0x284] - (discount//76 + 1)) & 0xff
    tim_cnt = (tim_cnt - discount) % tim_prescaler


    # RIOT
    riot_addr  = cpu.riot_addr
    riot_value = cpu.riot_value
    if cpu.RIOT_UPDATE:
        cpu.RIOT_UPDATE = False
        RIOT_update()
    
    # TIA: Register update
    if cpu.TIA_UPDATE:
        cpu.TIA_UPDATE = False
        tia.write(cpu.tia_addr)
        #replacement to remove TIA processing
        #if mem_write == 1 and addr < 0x80:
        #    if addr == TIA.VSYNC:
        #        if tia.system.memory[TIA.VSYNC] == 0 and tia.vsync != 0:
        #            tia.vsync = 2
        #        tia.vsync = tia.system.memory[TIA.VSYNC] 
        #    elif addr == TIA.WSYNC:
        #        tia.wsync = 1
        #        tia.system.clk_cycles = 228
        #    elif addr == TIA.RSYNC:
        #        tia.rsync = 1
        #        tia.system.clk_cycles = 225

    # TIA: draw TV line
    if system.clk_cycles >= 228:

        tia.line_update()
        #replacement to remove TIA processing
        tia.system.clk_cycles %= 228

        tia._prepare_next_line()
        #replacement to remove TIA processing
        #tia.line += 1
        if tia.vsync == 2:
            tia.vsync = 0
            tia.frame_update()
            tia.line = 3

            t2 = time.time()
            print("{} Hz, frame {}".format( 1/(t2-t1), frame_cnt))
            #code.interact(local=locals())
            frame_cnt += 1
            t1 = t2

time.sleep(2)
