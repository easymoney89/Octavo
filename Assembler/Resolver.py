#! /usr/bin/python3

from sys import exit
from Utility import Utility
from Debug import Debug
from Data import Pointer_Variable

class Resolver (Utility, Debug):
    """Takes the allocated intermediate structures and resolves names, addresses, and code. The final result gets used for binary image generation."""

    def __init__ (self, data, code, configuration):
        Utility.__init__(self)
        Debug.__init__(self)
        self.data           = data
        self.code           = code
        self.configuration  = configuration

    def resolve (self):
        self.resolve_read_operands()
        self.resolve_write_operands()
        self.resolve_pointers()
        self.resolve_instruction_addresses()
        self.resolve_branches()
#        self.resolve_opcodes()
        self.resolve_program_counters()

    def resolve_read_operands (self, instruction_list = None):
        if instruction_list is None:
            instruction_list = self.code.all_instructions()
        for instruction in instruction_list:
            self.resolve_read_operand(instruction, "A")
            self.resolve_read_operand(instruction, "B")

    def resolve_read_operand (self, instruction, operand):
        value = getattr(instruction, operand)
        # Source is all strings, convert to int if possible
        value = self.try_int(value)
        # If it's a literal number, add it to the shared memory pool
        if type(value) == int:
            entry = self.data.resolve_shared_value(value, operand)
        # If it's a string, look it up and add it to whichever memory area it belongs to
        elif type(value) == str:
            entry = self.data.resolve_named(value, operand)
        else:
            print("Read operand value has unexpected type!: {0}".format(value))
            print(instruction)
            self.ask_for_debugger()
        setattr(instruction, operand, entry.address)
        return

    def resolve_write_operands (self, instruction_list = None):
        if instruction_list is None:
            instruction_list = self.code.all_instructions()
        for instruction in instruction_list:
            self.resolve_write_operand(instruction)

    def resolve_write_operand (self, instruction):
        is_dual = self.code.is_instruction_dual(instruction)
        if is_dual is True:
            self.resolve_write_operand_case(instruction, "DA")
            self.resolve_write_operand_case(instruction, "DB")
        else:
            self.resolve_write_operand_case(instruction, "D") 
#        print(instruction.opcode, instruction.D, instruction.A, instruction.B)

    def resolve_write_operand_case (self, instruction, operand):
        value = getattr(instruction, operand)
        # Source is all strings, convert to int if possible
        converted_value = self.try_int(value)
        # If its an int, nothing much to do.
        if type(converted_value) == int:
            setattr(instruction, operand, converted_value)
            return
        # If it's a string, look it up, and replace with its write address
        # The variable must have been used as a read operand before, so its
        # we have already set which memory it must reside in.
        elif type(converted_value) == str:
            variable = self.data.lookup_variable_name(converted_value)
            if variable is None:
                print("Unknown variable {0} used as write operand.".format(converted_value))
                print(instruction)
                self.ask_for_debugger()
            # But if it's a pointer, instead find another resolved pointer which points to the
            # same variable and use that memory name, converted to its equivalent write name.
            # At a minimum, this will be a previously resolved read pointer.
            if type(variable) is Pointer_Variable:
                for pointer in self.data.pointers:
                    if pointer.address is None:
                        continue
                    if variable == pointer:
                        continue
                    if variable.base == pointer.base:
                        if "D" not in pointer.memory:
                            variable.memory = "D" + pointer.memory
                        break
                if variable.memory is None:
                    print("Could not find a corresponding pointer for write pointer {0}".format(variable.label))
                    self.ask_for_debugger()
            variable      = self.data.resolve_named(converted_value, variable.memory)
            write_address = self.configuration.memory_map.read_to_write_address(variable.address, variable.memory)
            setattr(instruction, operand, write_address)
            return
        else:
            print("Write operand value has unexpected type!: {0}".format(converted_value))
            print(instruction)
            self.ask_for_debugger()

    def resolve_pointers (self):
        for pointer in self.data.pointers:
            self.resolve_pointer(pointer)

    def resolve_pointer (self, pointer):
        # Lookup pointed-to variable
        variable = self.data.lookup_variable_name(pointer.base)
        # Now resolve the pointed-to variable, if necessary
        if variable.memory is not None:
            # Special case: variables are in memory A or B, pointers in A, B, DA, DB so a substring search suffices.
            if variable.memory not in pointer.memory:
                print("Variable {0} already assigned to memory {1} but pointer {2} is in memory {3}".format(variable.label, variable.memory, pointer.label, pointer.memory))
                self.ask_for_debugger()
        else:
            variable.memory = pointer.memory
            # But use the read name of the memory for the variable
            if variable.memory == "DA":
                variable.memory == "A"
            if variable.memory == "DB":
                variable.memory == "B"
        if variable.address is None:
            variable.address  = self.data.next_variable_address(variable, variable.memory)
        # Resolve the pointer base address
        pointer.base = variable.address
        # Now construct the init load for this pointer
        init_load = self.code.lookup_init_load(pointer.label)
        # Used later to resolve the init load data for this pointer
        pointer.init_load = init_load
        init_label = pointer.label + "_init"
        init_load.add_private(init_label, pointer.threads)
        init_address = self.configuration.memory_map.po[pointer.memory][pointer.slot]
        self.code.usage.allocate_po(pointer.label, pointer.memory)
        instr  = init_load.add_instruction(init_load.label, init_address, init_label)
        self.resolve_read_operands([instr])
        # Put the next pointer init data in the other memory (evens out storage)
        init_load.toggle_memory()

    def resolve_instruction_addresses (self):
        """After all instructions are allocated and their operands resolved, we can sequentially give them addresses."""
        address = 0
        for instruction in self.code.all_instructions():
            if address == self.configuration.memory_depth_words:
                print("Out of code memory!")
                self.ask_for_debugger()
            instruction.address = address
            address += 1

    def resolve_branches (self):
        for branch in self.code.branches:
            self.resolve_branch(branch)

    def resolve_branch (self, branch):
        """After the instruction addresses are known, we can finish filling-in the Branch data. (e.g.: destination and origins)"""
        # Resolve the branch origin address
        branch.origin = branch.instruction.address
        if branch.origin is None or type(branch.origin) is not int:
            print("Instruction {0} did not have an address when resolving origin {1} of associated branch {2}".format(branch.instruction, branch.origin, branch))
            self.ask_for_debugger()
        # Resolve the branch destination address (we have the instruction label already)
        destination_instruction = self.code.lookup_instruction(branch.destination)
        if destination_instruction is None:
            print("No instruction with label {0} found when resolving branch {1} destination".format(branch.destination, branch))
            self.ask_for_debugger()
        branch.destination = destination_instruction.address
        if branch.destination is None or type(branch.destination) is not int:
            print("Instruction {0} did not have an address when resolving destination {1} of associated branch {2}".format(branch.instruction, branch.destination, branch))
            self.ask_for_debugger()

#    def resolve_opcodes (self, instruction_list = None):
#        if instruction_list is None:
#            instruction_list = self.code.all_instructions()
#        for instruction in instruction_list:
#            self.resolve_opcode(instruction)

#    def resolve_opcode (self, instruction):
#        """Convert opcode label into opcode number. Number depends on the order of the opcode definitions."""
#        opcode = self.code.lookup_opcode(instruction.opcode)
#        number = self.code.opcodes.index(opcode)
#        instruction.opcode = number

    def resolve_program_counters (self):
        """Convert code labels for thread initial start points into instruction addresses."""
        pc_list = self.code.initial_pc
        for thread_number in range(len(pc_list)):
            start_label = pc_list[thread_number]
            instruction = self.code.lookup_instruction(start_label)
            pc_list[thread_number] = instruction.address

