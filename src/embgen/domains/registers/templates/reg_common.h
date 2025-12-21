#pragma once

#include <stdint.h>

#define REG_FIELD_SIZE 2

#if REG_FIELD_SIZE == 1
typedef uint8_t reg_field_t;
#define REG_HEADER_SIZE 2 // [addr|rw, length]
#elif REG_FIELD_SIZE == 2
typedef uint16_t reg_field_t;
#define REG_HEADER_SIZE 4 // [addr_h|rw, addr_l, len_h, len_l]
#elif REG_FIELD_SIZE == 4
typedef uint32_t reg_field_t;
#define REG_HEADER_SIZE 8 // [addr_hh|rw, addr_hl, addr_lh, addr_ll, len_hh, len_hl, len_lh, len_ll]
#else
#error "Unsupported REG_FIELD_SIZE"
#endif

typedef enum
{
    REG_ATTR_NONE = 0,
    REG_ATTR_READONLY = (1 << 0),
    REG_ATTR_WRITEONLY = (1 << 1),
} reg_attr_t;

// Header is raw bytes - use helper functions to encode/decode
typedef struct __attribute__((packed)) reg_header
{
    uint8_t data[REG_HEADER_SIZE];
} reg_header_t;

void reg_header_encode(reg_header_t *h, uint8_t is_read, reg_field_t addr, reg_field_t length);
void reg_header_decode(const reg_header_t *h, uint8_t *is_read, reg_field_t *addr, reg_field_t *length);