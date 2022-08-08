import sys

def print_debug(text):
    pass
    #print(text)


class cpu:

    MAX_MEM_ADDR = 0x1fff # 8KB-1 (13-bits)


    def __init__(self, system):

        self.A = self.X = self.Y = 0                      # Registers
        self.PC = 0                             # Program counter
        self.SP = 0                             # Stack pointer
        self.N = self.V = self.B = self.D = self.I = self.Z = self.C = False  # Status flags

        self.system = system

        self.page_crossed = 0
        self.frame_cnt = 0
        self.total_cycles = 0
        #
        self.TIA_UPDATE = False
        self.tia_addr  = 0
        self.tia_value = 0
        
        #RIOT (PIA 6532)
        self.RIOT_UPDATE = False
        self.riot_addr  = 0
        self.riot_value = 0

        self.mem_write = 0
        self.mem_read = 0
        
        
        # opcodes table
        self.opcode_table = [[self.unknown, self.IMMEDIATE, 0, 0, 0] for x in range(256)]
        #                    [operation, Addresing mode,        bytes, cycles, add_page_crossed]
        # ADD
        self.opcode_table[0x69] = [self.adc_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0x65] = [self.adcMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0x75] = [self.adcMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0x6d] = [self.adcMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0x7d] = [self.adcMem_,   self.MEM_READ_ABSOLUTE_X,   3,     4,      1]
        self.opcode_table[0x79] = [self.adcMem_,   self.MEM_READ_ABSOLUTE_Y,   3,     4,      1]
        self.opcode_table[0x61] = [self.adcMem_,   self.MEM_READ_INDIRECT_X,   2,     6,      0]
        self.opcode_table[0x71] = [self.adcMem_,   self.MEM_READ_INDIRECT_Y,   2,     5,      1]
        
        # AND
        self.opcode_table[0x29] = [self.and_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0x25] = [self.andMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0x35] = [self.andMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0x2d] = [self.andMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0x3d] = [self.andMem_,   self.MEM_READ_ABSOLUTE_X,   3,     4,      1]
        self.opcode_table[0x39] = [self.andMem_,   self.MEM_READ_ABSOLUTE_Y,   3,     4,      1]
        self.opcode_table[0x21] = [self.andMem_,   self.MEM_READ_INDIRECT_X,   2,     6,      0]
        self.opcode_table[0x31] = [self.andMem_,   self.MEM_READ_INDIRECT_Y,   2,     5,      1]
        
        # ASL
        self.opcode_table[0x0a] = [self.aslAcc_,   self.IMMEDIATE,             1,     2,      0]
        self.opcode_table[0x06] = [self.aslMem_,   self.MEM_READ_ZEROPAGE,     2,     5,      0]
        self.opcode_table[0x16] = [self.aslMem_,   self.MEM_READ_ZEROPAGE_X,   2,     6,      0]
        self.opcode_table[0x0e] = [self.aslMem_,   self.MEM_READ_ABSOLUTE,     3,     6,      0]
        self.opcode_table[0x1e] = [self.aslMem_,   self.MEM_READ_ABSOLUTE_X,   3,     7,      0]
        
        # BCC                 self.           self.                    
        self.opcode_table[0x90] = [self.bcc_,      self.RELATIVE,              2,     2,      0]
        
        # BCS                 self.           self.                       
        self.opcode_table[0xb0] = [self.bcs_,      self.RELATIVE,              2,     2,      0]
        
        # BEQ                 self.           self.                       
        self.opcode_table[0xf0] = [self.beq_,      self.RELATIVE,              2,     2,      0]
        
        # BIT
        self.opcode_table[0x24] = [self.bit_,      self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0x2c] = [self.bit_,      self.MEM_READ_ABSOLUTE,     3,     4,      0]
        
        # BMI
        self.opcode_table[0x30] = [self.bmi_,      self.RELATIVE,              2,     2,      0]
        
        # BNE                 self.           self.                       
        self.opcode_table[0xd0] = [self.bne_,      self.RELATIVE,              2,     2,      0]
        
        # BPL                 self.           self.                       
        self.opcode_table[0x10] = [self.bpl_,      self.RELATIVE,              2,     2,      0]
        
        # BRK                 self.           self.                       
        self.opcode_table[0x00] = [self.brk_,      self.NONE,                  1,     7,      0]
        
        # BVC                 self.           self.                       
        self.opcode_table[0x50] = [self.bvc_,      self.RELATIVE,              2,     2,      0]
        
        # BVS
        self.opcode_table[0x70] = [self.bvs_,      self.RELATIVE,              2,     2,      0]
        
        # CLC                 self.           self.                       
        self.opcode_table[0x18] = [self.clc_,      self.NONE,                  1,     2,      0]
        
        # CLD                 self.           self.                       
        self.opcode_table[0xd8] = [self.cld_,      self.NONE,                  1,     2,      0]
        
        # CLI                 self.           self.                       
        self.opcode_table[0x58] = [self.cli_,      self.NONE,                  1,     2,      0]
        
        # CLV                 self.           self.                       
        self.opcode_table[0xb8] = [self.clv_,      self.NONE,                  1,     2,      0]
        
        # CMP                 self.           self.                    
        self.opcode_table[0xc9] = [self.cmp_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0xc5] = [self.cmpMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0xd5] = [self.cmpMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0xcd] = [self.cmpMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0xdd] = [self.cmpMem_,   self.MEM_READ_ABSOLUTE_X,   3,     4,      1]
        self.opcode_table[0xd9] = [self.cmpMem_,   self.MEM_READ_ABSOLUTE_Y,   3,     4,      1]
        self.opcode_table[0xc1] = [self.cmpMem_,   self.MEM_READ_INDIRECT_X,   2,     6,      0]
        self.opcode_table[0xd1] = [self.cmpMem_,   self.MEM_READ_INDIRECT_Y,   2,     5,      1]
        
        # CPX
        self.opcode_table[0xe0] = [self.cpx_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0xe4] = [self.cpxMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0xec] = [self.cpxMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        
        # CPY
        self.opcode_table[0xc0] = [self.cpy_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0xc4] = [self.cpyMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0xcc] = [self.cpyMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        
        # DEC
        self.opcode_table[0xc6] = [self.decMem_,   self.MEM_READ_ZEROPAGE,     2,     5,      0]
        self.opcode_table[0xd6] = [self.decMem_,   self.MEM_READ_ZEROPAGE_X,   2,     6,      0]
        self.opcode_table[0xce] = [self.decMem_,   self.MEM_READ_ABSOLUTE,     3,     6,      0]
        self.opcode_table[0xde] = [self.decMem_,   self.MEM_READ_ABSOLUTE_X,   3,     7,      0]
        
        # DEX
        self.opcode_table[0xca] = [self.dex_,      self.MEM_READ_ZEROPAGE,     1,     2,      0]
        
        # DEY
        self.opcode_table[0x88] = [self.dey_,      self.MEM_READ_ZEROPAGE,     1,     2,      0]
        
        # EOR
        self.opcode_table[0x49] = [self.eor_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0x45] = [self.eorMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0x55] = [self.eorMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0x4d] = [self.eorMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0x5d] = [self.eorMem_,   self.MEM_READ_ABSOLUTE_X,   3,     4,      1]
        self.opcode_table[0x59] = [self.eorMem_,   self.MEM_READ_ABSOLUTE_Y,   3,     4,      1]
        self.opcode_table[0x41] = [self.eorMem_,   self.MEM_READ_INDIRECT_X,   2,     6,      0]
        self.opcode_table[0x51] = [self.eorMem_,   self.MEM_READ_INDIRECT_Y,   2,     5,      1]
        
        # INC
        self.opcode_table[0xe6] = [self.incMem_,   self.MEM_READ_ZEROPAGE,     2,     5,      0]
        self.opcode_table[0xf6] = [self.incMem_,   self.MEM_READ_ZEROPAGE_X,   2,     6,      0]
        self.opcode_table[0xee] = [self.incMem_,   self.MEM_READ_ABSOLUTE,     3,     6,      0]
        self.opcode_table[0xfe] = [self.incMem_,   self.MEM_READ_ABSOLUTE_X,   3,     7,      0]
        
        # INX
        self.opcode_table[0xe8] = [self.inx_,      self.MEM_READ_ZEROPAGE,     1,     2,      0]
        
        # INY
        self.opcode_table[0xc8] = [self.iny_,      self.MEM_READ_ZEROPAGE,     1,     2,      0]
        
        # JMP
        self.opcode_table[0x4c] = [self.jmp_,      self.MEM_READ_ABSOLUTE,     3,     3,      0]
        self.opcode_table[0x6c] = [self.jmp_,      self.MEM_READ_INDIRECT,     3,     5,      0]
        
        # JSR
        self.opcode_table[0x20] = [self.jsr_,      self.MEM_READ_ABSOLUTE,     3,     6,      0]
        
        # LDA
        self.opcode_table[0xa9] = [self.lda_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0xa5] = [self.ldaMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0xb5] = [self.ldaMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0xad] = [self.ldaMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0xbd] = [self.ldaMem_,   self.MEM_READ_ABSOLUTE_X,   3,     4,      1]
        self.opcode_table[0xb9] = [self.ldaMem_,   self.MEM_READ_ABSOLUTE_Y,   3,     4,      1]
        self.opcode_table[0xa1] = [self.ldaMem_,   self.MEM_READ_INDIRECT_X,   2,     6,      0]
        self.opcode_table[0xb1] = [self.ldaMem_,   self.MEM_READ_INDIRECT_Y,   2,     5,      1]
        
        # LDX
        self.opcode_table[0xa2] = [self.ldx_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0xa6] = [self.ldxMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0xb6] = [self.ldxMem_,   self.MEM_READ_ZEROPAGE_Y,   2,     4,      0]
        self.opcode_table[0xae] = [self.ldxMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0xbe] = [self.ldxMem_,   self.MEM_READ_ABSOLUTE_Y,   3,     4,      1]
        
        # LDY
        self.opcode_table[0xa0] = [self.ldy_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0xa4] = [self.ldyMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0xb4] = [self.ldyMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0xac] = [self.ldyMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0xbc] = [self.ldyMem_,   self.MEM_READ_ABSOLUTE_X,   3,     4,      1]
        
        # LSR
        self.opcode_table[0x4a] = [self.lsr_,      self.IMMEDIATE,             1,     2,      0]
        self.opcode_table[0x46] = [self.lsrMem_,   self.MEM_READ_ZEROPAGE,     2,     5,      0]
        self.opcode_table[0x56] = [self.lsrMem_,   self.MEM_READ_ZEROPAGE_X,   2,     6,      0]
        self.opcode_table[0x4e] = [self.lsrMem_,   self.MEM_READ_ABSOLUTE,     3,     6,      0]
        self.opcode_table[0x5e] = [self.lsrMem_,   self.MEM_READ_ABSOLUTE_X,   3,     7,      0]
        
        # NOP
        self.opcode_table[0xea] = [self.nop_,      self.IMMEDIATE,             1,     2,      0]
        
        # ORA
        self.opcode_table[0x09] = [self.ora_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0x05] = [self.oraMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0x15] = [self.oraMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0x0d] = [self.oraMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0x1d] = [self.oraMem_,   self.MEM_READ_ABSOLUTE_X,   3,     4,      1]
        self.opcode_table[0x19] = [self.oraMem_,   self.MEM_READ_ABSOLUTE_Y,   3,     4,      1]
        self.opcode_table[0x01] = [self.oraMem_,   self.MEM_READ_INDIRECT_X,   2,     6,      0]
        self.opcode_table[0x11] = [self.oraMem_,   self.MEM_READ_INDIRECT_Y,   2,     5,      1]
        
        # PHA
        self.opcode_table[0x48] = [self.pha_,      self.IMMEDIATE,             1,     3,      0]
        
        # PHP
        self.opcode_table[0x08] = [self.php_,      self.IMMEDIATE,             1,     3,      0]
        
        # PLA
        self.opcode_table[0x68] = [self.pla_,      self.IMMEDIATE,             1,     4,      0]
        
        # PLP
        self.opcode_table[0x28] = [self.plp_,      self.IMMEDIATE,             1,     4,      0]
        
        # ROL
        self.opcode_table[0x2a] = [self.rol_,      self.IMMEDIATE,             1,     2,      0]
        self.opcode_table[0x26] = [self.rolMem_,   self.MEM_READ_ZEROPAGE,     2,     5,      0]
        self.opcode_table[0x36] = [self.rolMem_,   self.MEM_READ_ZEROPAGE_X,   2,     6,      0]
        self.opcode_table[0x2e] = [self.rolMem_,   self.MEM_READ_ABSOLUTE,     3,     6,      0]
        self.opcode_table[0x3e] = [self.rolMem_,   self.MEM_READ_ABSOLUTE_X,   3,     7,      0]
        
        # ROR                 self.           self.                     
        self.opcode_table[0x6a] = [self.ror_,      self.IMMEDIATE,             1,     2,      0]
        self.opcode_table[0x66] = [self.rorMem_,   self.MEM_READ_ZEROPAGE,     2,     5,      0]
        self.opcode_table[0x76] = [self.rorMem_,   self.MEM_READ_ZEROPAGE_X,   2,     6,      0]
        self.opcode_table[0x6e] = [self.rorMem_,   self.MEM_READ_ABSOLUTE,     3,     6,      0]
        self.opcode_table[0x7e] = [self.rorMem_,   self.MEM_READ_ABSOLUTE_X,   3,     7,      0]
        
        #TODO: Voy por aqui
        # RTI                 self.           self.                    
        self.opcode_table[0x40] = [self.rti_,      self.NONE,                  1,     6,      0]
        
        # RTS                 self.           self.                             
        self.opcode_table[0x60] = [self.rts_,      self.NONE,                  1,     6,      0]
        
        # SBC                 self.           self.                    
        self.opcode_table[0xe9] = [self.sbc_,      self.IMMEDIATE,             2,     2,      0]
        self.opcode_table[0xe5] = [self.sbcMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0xf5] = [self.sbcMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0xed] = [self.sbcMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0xfd] = [self.sbcMem_,   self.MEM_READ_ABSOLUTE_X,   3,     4,      1]
        self.opcode_table[0xf9] = [self.sbcMem_,   self.MEM_READ_ABSOLUTE_Y,   3,     4,      1]
        self.opcode_table[0xe1] = [self.sbcMem_,   self.MEM_READ_INDIRECT_X,   2,     6,      0]
        self.opcode_table[0xf1] = [self.sbcMem_,   self.MEM_READ_INDIRECT_Y,   2,     5,      1]
        
        # SEC
        self.opcode_table[0x38] = [self.sec_,      self.NONE,                  1,     2,      0]
        
        # SED
        self.opcode_table[0xf8] = [self.sed_,      self.NONE,                  1,     2,      0]
        
        # SEI
        self.opcode_table[0x78] = [self.sei_,      self.NONE,                  1,     2,      0]
        
        # STA                 self.           self.                    
        self.opcode_table[0x85] = [self.staMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0x95] = [self.staMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0x8d] = [self.staMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        self.opcode_table[0x9d] = [self.staMem_,   self.MEM_READ_ABSOLUTE_X,   3,     5,      0]
        self.opcode_table[0x99] = [self.staMem_,   self.MEM_READ_ABSOLUTE_Y,   3,     5,      0]
        self.opcode_table[0x81] = [self.staMem_,   self.MEM_READ_INDIRECT_X,   2,     6,      0]
        self.opcode_table[0x91] = [self.staMem_,   self.MEM_READ_INDIRECT_Y,   2,     6,      0]
        
        # STX                 self.           self.                    
        self.opcode_table[0x86] = [self.stxMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0x96] = [self.stxMem_,   self.MEM_READ_ZEROPAGE_Y,   2,     4,      0]
        self.opcode_table[0x8e] = [self.stxMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        
        # STY                 self.           self.                    
        self.opcode_table[0x84] = [self.styMem_,   self.MEM_READ_ZEROPAGE,     2,     3,      0]
        self.opcode_table[0x94] = [self.styMem_,   self.MEM_READ_ZEROPAGE_X,   2,     4,      0]
        self.opcode_table[0x8c] = [self.styMem_,   self.MEM_READ_ABSOLUTE,     3,     4,      0]
        
        # TAX                 self.           self.                    
        self.opcode_table[0xaa] = [self.tax_,      self.NONE,                  1,     2,      0]
        
        # TAY                 self.           self.                       
        self.opcode_table[0xa8] = [self.tay_,      self.NONE,                  1,     2,      0]
        
        # TSX                 self.           self.                       
        self.opcode_table[0xba] = [self.tsx_,      self.NONE,                  1,     2,      0]
        
        # TSA                 self.           self.                       
        self.opcode_table[0x8a] = [self.tsa_,      self.NONE,                  1,     2,      0]
        
        # TXS                 self.           self.                       
        self.opcode_table[0x9a] = [self.txs_,      self.NONE,                  1,     2,      0]
        
        # TYA                 self.           self.                       
        self.opcode_table[0x98] = [self.tya_,      self.NONE,                  1,     2,      0]


    # Memory bus operation
    def MEM_WRITE(self, addr, value):
    
        self.mem_write = 1
    
        addr &= cpu.MAX_MEM_ADDR
    
        if addr >= 0x40 and addr < 0x80:
            print_debug("ZERO PAGE 0x{:02X}".format(addr))
            addr -= 0x40
            #sys.exit()
    
        if addr != 0x282: # Port B is hardwired as input. Ignore write operations on it
            self.system.memory[addr] = value
        
        #if addr > 0x30 and addr < 0x3f:
        #    print( 'WTF' )
        #    #sys.exit()
    
        # TIA register (0x00 - 0x80)
        if addr < 0x80:
            self.TIA_UPDATE = True
            self.tia_addr  = addr
            self.tia_value = value
    
            if addr > 0x3f:
                print_debug('W_ADDR {}'.format(hex(addr)))
    
        if addr >= 0x280:
            self.RIOT_UPDATE = True
            self.riot_addr  = addr
            self.riot_value = value
            print_debug('W_ADDR 0x{:4X}, val:{}'.format(addr, value))
    
                
    def MEM_READ(self, addr):
    
        self.mem_read = 1
    
        addr &= cpu.MAX_MEM_ADDR
    
        if addr >= 0x40 and addr < 0x80:
            print_debug("ZERO PAGE {}".format(addr))
            addr -= 0x40
            sys.exit()
    
        if addr < 0x0E or (addr >= 0x30 and addr < 0x3E):
            addr = (addr & 0x0F) + 0x100 # fake address for read-only TIA registers
        #    return tia_rd[addr & 0x0F]
    
        return self.system.memory[addr]
    
    #
    # addressing modes
    #
    # READ
    def NONE(self, val):
        return 0
    
    def IMMEDIATE(self, val):
        return val
    
    def RELATIVE(self, addr):
        if addr < 128:
            return addr
        else:
            return (addr - 0x100)
    
    def MEM_READ_ZEROPAGE(self, addr):
        return addr & 0xff
    
    def MEM_READ_ZEROPAGE_X(self, addr):
        return (addr + self.X) & 0xff
    
    def MEM_READ_ZEROPAGE_Y(self, addr):
        return (addr + self.Y) & 0xff
    
    def MEM_READ_ABSOLUTE(self, addr):
    
        return addr
    
    # Not clear the 'page_crossed' extra cycle: https://wiki.nesdev.com/w/index.php/CPU_addressing_modes
    def MEM_READ_ABSOLUTE_X(self, addr):
    
        addr = addr + self.X
        if (addr & 0xff) < self.X: self.page_crossed = 1
        return addr
    
    def MEM_READ_ABSOLUTE_Y(self, addr):
    
        addr = addr + self.Y
        if (addr & 0xff) < self.Y: self.page_crossed = 1
        return addr
    
    def MEM_READ_INDIRECT(self, addrL):
        # HW Bug in original 6502 processor (instead of addrH = addrL+1)
        addrH = (addrL & 0xff00) | ((addrL + 1) & 0x00ff)
        addr = self.MEM_READ(addrL) | (self.MEM_READ(addrH)<<8)
    
        return addr
    
    def MEM_READ_INDIRECT_X(self, addr):
        addr = (addr + X) & 0xff
        addr = self.MEM_READ(addr) | (self.MEM_READ((addr + 1) & 0xff) << 8)
        return addr
    
    def MEM_READ_INDIRECT_Y(self, addr):
        
        addr = self.MEM_READ(addr) | (self.MEM_READ((addr + 1) & 0xff) << 8)
        addr = addr + self.Y
        if (addr & 0xff) < self.Y: self.page_crossed = 1
        return addr
    
    #TODO: maybe delete this macros
    # WRITE
    def MEM_WRITE_ZEROPAGE(self, addr, val):
        self.MEM_WRITE(addr & 0xff, val)
    
    def MEM_WRITE_ZEROPAGE_X(self, addr, val):
        self.MEM_WRITE((addr +  self.X) & 0xff, val)
    #
    def MEM_WRITE_ZEROPAGE_Y(self, addr, val):
        self.MEM_WRITE((addr +  self.Y) & 0xff, val)
    
    def MEM_WRITE_ABSOLUTE(self, addr, val):
        self.MEM_WRITE(addr, val)
    
    def MEM_WRITE_ABSOLUTE_X(self, addr, val):
        self.MEM_WRITE((addr + self.X), val)    
    
    def MEM_WRITE_ABSOLUTE_Y(self, addr, val):
        self.MEM_WRITE((addr + self.Y), val)    
        
    #def MEM_WRITE_MEM_READ_INDIRECT(addr, val):
    #    addr = self.system.memory[addr] | slef.system.memory[addr + 1]<<8
    #    self.MEM_WRITE(addr & cpu.MAX_MEM_ADDR, val)
        
    def MEM_WRITE_INDIRECT_X(self, addr, val):
        addr = (addr+ X) & 0xff
        addr = self.MEM_READ(addr) | (self.MEM_READ(addr+1)<<8)
        self.MEM_WRITE(addr, val)
    
    def MEM_WRITE_INDIRECT_Y(self, addr, val):
        addr = self.MEM_READ(addr) | (self.MEM_READ(addr+1)<<8)
        addr = addr + Y
        self.MEM_WRITE(addr, val)

    #
    # Flags status byte
    #
    def PSW_GET(self):
        tmp = 0
        if self.C == True: tmp |= 0x01 # inventado..mirar status byte 
        if self.Z == True: tmp |= 0x02
        if self.I == True: tmp |= 0x04
        if self.D == True: tmp |= 0x08
        if self.B == True: tmp |= 0x10
        if self.V == True: tmp |= 0x20
        if self.N == True: tmp |= 0x40
        return tmp
    
    def PSW_SET(self, val):
        
        self.C = val&0x01 != 0
        self.Z = val&0x02 != 0
        self.I = val&0x04 != 0
        self.D = val&0x08 != 0
        self.B = val&0x10 != 0
        self.V = val&0x20 != 0
        self.N = val&0x40 != 0

    #
    # Opcodes definition
    #
    
    # Unknown opcode
    def unknown(self, unused):
        print("opcode not implemented")
        return 0
    
    # ADC
    def adc_(self, val):
    
        res = self.A + val + self.C
        self.C = res > 255
        res &= 0xff
        self.V = (self.A^res)&(val^res)&0x80 != 0
        self.Z = res == 0
        self.N = (res & 0x80) != 0
        self.A = res
    
        return 0
    
    def adcMem_(self, addr):
        return self.adc_(self.MEM_READ(addr))
    
    # AND
    def and_(self, val):
    
        self.A = (self.A & val)
        self.Z = (self.A == 0)
        self.N = (self.A & 0x80) != 0
    
        return 0
    
    def andMem_(self, addr):
        return self.and_(self.MEM_READ(addr))
    
    # ASL
    def aslAcc_(self, unused):
    
        res = self.A << 1
        self.A = res & 0xff
        self.C = (res > 0xff)
        self.Z = (self.A == 0)
        self.N = (self.A & 0x80) != 0
    
        return 0
    
    
    def aslMem_(self, addr):
    
        res = self.MEM_READ(addr) << 1
        val = res & 0xff
        self.MEM_WRITE(addr, val)
        self.C = (res > 0xff)
        self.Z = (val == 0)
        self.N = (val & 0x80) != 0
    
        return 0
    
    # Any branch
    def bAny_(self, addr, taken):
    
        if taken:
            curr_PC  = self.PC
            self.PC += addr
            extra_cycles = 2 if ((curr_PC & 0xff00) != (self.PC & 0xff00)) else 1
        else:
            extra_cycles = 0
    
        return extra_cycles
    
    # BCC
    def bcc_(self, addr):
        return self.bAny_(addr, self.C == False)
    
    # BCS
    def bcs_(self, addr):
        return self.bAny_(addr, self.C == True)
    
    # BEQ
    def beq_(self, addr):
        return self.bAny_(addr, self.Z == True)
    
    # BIT
    def bit_(self, addr):
    
        val = self.MEM_READ(addr)
        self.Z = (val & self.A) == 0
        self.V = (val & 0x40) != 0
        self.N = (val & 0x80) != 0
    
        return 0
    
    # BMI
    def bmi_(self, addr):
        return self.bAny_(addr, self.N == True)
    
    # BNE
    def bne_(self, addr):
        return self.bAny_(addr, self.Z == False)
    
    # BPL
    def bpl_(self, addr):
        return self.bAny_(addr, self.N == False)
    
    # BRK
    def brk_(self, unused):
    
        self.B = 1
        # push PC and SP to stack
        rti_PC = self.PC + 1
        self.system.memory[self.SP]     = rti_PC >> 8
        self.system.memory[self.SP - 1] = rti_PC & 0xff
        self.system.memory[self.SP - 2] = self.PSW_GET()
        self.SP -= 3
        # PC = interrupt vector
        self.PC = (self.MEM_READ(self.MEM_READ_ABSOLUTE(0xfffe)) | self.MEM_READ(self.MEM_READ_ABSOLUTE(0xffff))<<8)
        print_debug(hex(self.PC))
    
        return 0
    
    # BVC
    def bvc_(self, addr):
        return self.bAny_(addr, self.V == False)
    
    # BVC
    def bvs_(self, addr):
        return self.bAny_(addr, self.V == True)
    
    # CLC
    def clc_(self, val):
    
        self.C = False
    
        return 0
    
    # CLD
    def cld_(self, val):
    
        self.D = False
    
        return 0    
    
    # CLI
    def cli_(self, val):
    
        self.I = False
    
        return 0
    
    # CLV
    def clv_(self, val):
    
        self.V = False
    
        return 0
        
    # CMP
    def cmp_(self, val):
    
        self.Z = self.A == val
        self.C = self.A >= val
        self.N = (((self.A - val)%256) & 0x80) != 0
    
        return 0
    
    def cmpMem_(self, addr):
        return cmp_(self.MEM_READ(addr))
    
    # CPX
    def cpx_(self, val):
    
        self.Z = self.X == val
        self.C = self.X >= val
        self.N = (((self.X - val)%256) & 0x80) != 0
    
        return 0
    
    def cpxMem_(self, addr):
        return cpx_(self.MEM_READ(addr))
    
    # CPY
    def cpy_(self, val):
    
        self.Z = self.Y == val
        self.C = self.Y >= val
        self.N = (((self.Y - val)%256) & 0x80) != 0
    
        return 0
    
    def cpyMem_(self, addr):
        return cpy_(self.MEM_READ(addr))
    
    # DEC
    def decMem_(self, addr):
    
        val = (self.MEM_READ(addr) - 1) & 0xff
        self.MEM_WRITE(addr, val)
        self.Z = val == 0
        self.N = (val & 0x80) != 0
    
        return 0
    
    # DEX
    def dex_(self, val):
    
        self.X = (self.X - 1) & 0xff
        self.Z = (self.X == 0)
        self.N = (self.X & 0x80) != 0
    
        return 0
    
    # DEY
    def dey_(self, val):
    
        self.Y = (self.Y - 1) & 0xff 
        self.Z = (self.Y == 0)
        self.N = (self.Y & 0x80) != 0
    
        return 0
    
    # EOR
    def eor_(self, val):
    
        self.A ^= val
        self.Z = self.A == 0
        self.N = (self.A & 0x80) != 0
    
        return 0
    
    def eorMem_(self, addr):
    
        val = self.MEM_READ(addr)
        self.A ^= val
        self.Z = self.A == 0
        self.N = (self.A & 0x80) != 0
    
        return 0
    
    # INC
    def incMem_(self, addr):
    
        val = (self.MEM_READ(addr) + 1) & 0xff
        self.MEM_WRITE_ZEROPAGE(addr, val)
        self.Z = val == 0
        self.N = (val & 0x80) != 0
    
        return 0
    
    def inx_(self, val):    
    
        self.X = (self.X + 1) & 0xff
        self.Z = (self.X == 0)
        self.N = (self.X & 0x80) != 0
    
        return 0
    
    def iny_(self, val):    
    
        self.Y = (self.Y + 1) & 0xff
        self.Z = (self.Y == 0)
        self.N = (self.Y & 0x80) != 0
    
        return 0
    
    # JMP
    def jmp_(self, val):    
        
        self.PC = val
    
        return 0
        
    # JSR
    def jsr_(self, val):
        # push PC-1 on to the stack
        self.PC -= 1
        self.system.memory[self.SP]     = self.PC >> 8
        self.system.memory[self.SP - 1] = self.PC & 0xff
        self.SP -= 2
        # update PC
        self.PC = val
    
        return 0
    
    # LDA
    def lda_(self, val):    
    
        self.A = val
        self.Z = self.A == 0
        self.N = (self.A & 0x80) != 0
        
        return 0
    
    def ldaMem_(self, addr):    
        return self.lda_(self.MEM_READ(addr))
    
    # LDX
    def ldx_(self, val):    
    
        self.X = val
        self.Z = self.X == 0
        self.N = (self.X & 0x80) != 0
    
        return 0
    
    def ldxMem_(self, addr):
        return self.ldx_(self.MEM_READ(addr))
    
    # LDY
    def ldy_(self, val):    
    
        self.Y = val
        self.Z = self.Y == 0
        self.N = (self.Y & 0x80) != 0
    
        return 0
    
    def ldyMem_(self, addr):
        return self.ldy_(self.MEM_READ(addr))
    
    # LSR
    def lsr_(self, unused):
        
        self.C = (self.A & 0x01) != 0
        self.A = (self.A >> 1)
        self.Z = (self.A == 0)
        self.N = (self.A & 0x80) != 0
        
        return 0
    
    def lsrMem_(self, addr):
        
        val = self.MEM_READ(addr)
        self.C = (val & 0x01) != 0
        val = val >> 1
        self.MEM_WRITE(addr, val)
        self.Z = (val == 0)
        self.N = (val & 0x80) != 0
        
        return 0
    
    def nop_(self, val):    
        return 0    
    
    def ora_(self, val):    
    
        self.A = (self.A | val)
        self.Z = (self.A == 0)
        self.N = (self.A & 0x80) != 0
    
        return 0
    
    def oraMem_(self, addr):    
        return self.ora_(self.MEM_READ(addr))
    
    def pha_(self, val):    
    
        self.system.memory[self.SP] = self.A
        self.SP = self.SP - 1
    
        return 0    
    
    def php_(self, val):
    
        self.system.memory[self.SP] = self.PSW_GET()
        self.SP = self.SP - 1
    
        return 0    
    
    def pla_(self, val):
    
        self.SP = self.SP + 1
        self.A  = self.system.memory[self.SP]
        self.Z  = self.A == 0 
        self.N  = (self.A & 0x80 != 0) 
    
        return 0
    
    def plp_(self, val):
    
        self.SP = self.SP + 1
        tmp = self.system.memory[self.SP]
        self.PSW_SET(tmp)
    
        return 0
    
    # ROL
    def rol_(self, val):
    
        res = (self.A << 1) | self.C # Mixing integer and boolean, but it is OK (True -> 1)
        self.A = res & 0xff
        self.C = res > 0xff
        self.Z = (self.A == 0)
        self.N = (self.A & 0x80) != 0    
    
        return 0
    
    def rolMem_(self, addr):
    
        res = (self.MEM_READ(addr) << 1) | self.C
        val = res & 0xff
        self.MEM_WRITE(addr, val)
        self.C = res > 0xff
        self.Z = (val == 0)
        self.N = (val & 0x80) != 0    
    
        return 0
    
    # ROR
    def ror_(self, val):
        
        bit0 = val & 0x01
        self.A = (val >> 1) | (self.C << 7) # Mixing integer and boolean, but it is OK (True -> 1)
        self.N = self.C
        self.C = (bit0 != 0)
        self.Z = (self.A == 0)
        
        return 0
    
    def rorMem_(self, addr):
        
        val = self.MEM_READ(addr)
        bit0 = val & 0x01
        res = (val >> 1) | (self.C << 7)
        self.MEM_WRITE(addr, res)
        self.N = self.C
        self.C = (bit0 != 0)
        self.Z = (res == 0)
        
        return 0
    
    
    # RTI
    def rti_(self, unused):
    
        self.PSW_SET(self.system.memory[self.SP + 1])
        self.PC = self.system.memory[self.SP + 2] | (self.system.memory[self.SP + 3] << 8)
        self.SP += 3
    
        return 0
    
    # RTS
    def rts_(self, unused):
    
        self.PC = (self.system.memory[self.SP + 1] | (self.system.memory[self.SP + 2] << 8)) + 1
        self.SP += 2
    
        return 0
    
    # SBC (DMG: BCD mode not implemented)
    def sbc_(self, val):
        return self.adc_(val ^ 0xff)
    
    def sbcMem_(self, addr):
        return self.sbc_(self.MEM_READ(addr))
    
    # SEC
    def sec_(self, unused):
    
        self.C = 1
    
        return 0
    
    # SED
    def sed_(self, unused):
    
        self.D = 1
    
        return 0    
    
    # SEI
    def sei_(self, unused):
    
        self.I = 1
    
        return 0
    
    # STA
    def staMem_(self, addr):
    
        self.MEM_WRITE(addr, self.A)
    
        return 0
    
    # STX
    def stxMem_(self, addr):
    
        self.MEM_WRITE(addr, self.X)
    
        return 0
    
    # STY
    def styMem_(self, addr):
    
        self.MEM_WRITE(addr, self.Y)
    
        return 0
    
    # TAX
    def tax_(self, unused):
    
        self.X = self.A
        self.Z = self.X == 0
        self.N = (self.X & 0x80) != 0
    
        return 0
    
    # TAY
    def tay_(self, unused):
    
        self.Y = self.A
        self.Z = self.Y == 0
        self.N = (self.Y & 0x80) != 0
    
        return 0    
    
    # TSX
    def tsx_(self, unused):
    
        self.X = self.SP
        self.Z = self.X == 0
        self.N = (self.X & 0x80) != 0
    
        return 0
    
    # TSA
    def tsa_(self, unused):
    
        self.A = self.X
        self.Z = self.A == 0
        self.N = (self.A & 0x80) != 0
    
        return 0
    
    # TXS
    def txs_(self, unused):
    
        self.SP = self.X
    
        return 0    
    
    # TYA
    def tya_(self, unused):
    
        self.A = self.Y
        self.Z = self.A == 0
        self.N = (self.A & 0x80) != 0
    
        return 0    
    

    def execute(self):

        self.page_crossed = 0

        self.mem_write = 0
        self.mem_read = 0

        # Get the next opcode
        print_debug("PC {}".format(hex(self.PC)))
        opcode = self.MEM_READ(self.PC)
#        print(hex(opcode))
        opFunc, opMode, nbytes, ncycles, add_page_crossed = self.opcode_table[opcode]
        
        if opFunc == self.unknown:
            print("Unknown opcode: {}".format(hex(opcode)))
            import sys
            sys.exit()

        # Get the operand (if appropriate)
        if nbytes == 2  : addr = opMode(self.MEM_READ(self.PC+1))
        elif nbytes == 3: addr = opMode(self.MEM_READ(self.PC+1) + (self.MEM_READ(self.PC+2)<<8))
        else            : addr = 0

        # Update PC
        self.PC += nbytes

        # Execute opcode
        extra_cycles  = opFunc(addr)
        extra_cycles += add_page_crossed * self.page_crossed

        # Update num cycles
        self.system.clk_cycles = self.system.clk_cycles + (ncycles + extra_cycles) * 3

        return (ncycles + extra_cycles)

