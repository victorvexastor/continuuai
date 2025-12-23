import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import { body, validationResult } from 'express-validator';

const router = express.Router();

// In-memory bookings store (replace with database in production)
const bookings = new Map();

/**
 * GET /api/calendar/slots
 * Get available time slots for a date range
 */
router.get('/slots', (req, res) => {
    const { startDate, endDate } = req.query;

    try {
        const allBookings = Array.from(bookings.values()).filter(booking => {
            const bookingDate = new Date(booking.startTime);
            return bookingDate >= new Date(startDate) && bookingDate <= new Date(endDate);
        });

        res.json({ bookings: allBookings });
    } catch (error) {
        console.error('Error fetching slots:', error);
        res.status(500).json({ error: 'Failed to fetch slots' });
    }
});

/**
 * POST /api/calendar/book
 * Create a new booking
 */
router.post('/book', [
    body('startTime').isISO8601(),
    body('endTime').isISO8601(),
    body('gpuCount').isInt({ min: 1, max: 4 })
], (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() });
    }

    const { userId, startTime, endTime, gpuCount } = req.body;

    // Check for conflicts
    const conflicts = Array.from(bookings.values()).filter(booking => {
        const bookingStart = new Date(booking.startTime);
        const bookingEnd = new Date(booking.endTime);
        const newStart = new Date(startTime);
        const newEnd = new Date(endTime);

        return (newStart < bookingEnd && newEnd > bookingStart);
    });

    if (conflicts.length > 0) {
        return res.status(409).json({
            error: 'Time slot conflict',
            conflicts: conflicts
        });
    }

    try {
        const id = uuidv4();
        const booking = {
            id,
            userId,
            startTime,
            endTime,
            gpuCount,
            status: 'pending',
            createdAt: new Date().toISOString()
        };

        bookings.set(id, booking);

        res.status(201).json({ booking });
    } catch (error) {
        console.error('Error creating booking:', error);
        res.status(500).json({ error: 'Failed to create booking' });
    }
});

/**
 * PUT /api/calendar/reschedule/:id
 * Update an existing booking
 */
router.put('/reschedule/:id', [
    body('startTime').isISO8601(),
    body('endTime').isISO8601()
], (req, res) => {
    const { id } = req.params;
    const { startTime, endTime } = req.body;

    const booking = bookings.get(id);

    if (!booking) {
        return res.status(404).json({ error: 'Booking not found' });
    }

    // Check for conflicts (excluding current booking)
    const conflicts = Array.from(bookings.values()).filter(b => {
        if (b.id === id) return false;

        const bookingStart = new Date(b.startTime);
        const bookingEnd = new Date(b.endTime);
        const newStart = new Date(startTime);
        const newEnd = new Date(endTime);

        return (newStart < bookingEnd && newEnd > bookingStart);
    });

    if (conflicts.length > 0) {
        return res.status(409).json({
            error: 'Time slot conflict',
            conflicts
        });
    }

    booking.startTime = startTime;
    booking.endTime = endTime;
    booking.updatedAt = new Date().toISOString();

    bookings.set(id, booking);

    res.json({ booking });
});

/**
 * DELETE /api/calendar/cancel/:id
 * Cancel a booking
 */
router.delete('/cancel/:id', (req, res) => {
    const { id } = req.params;

    if (!bookings.has(id)) {
        return res.status(404).json({ error: 'Booking not found' });
    }

    const booking = bookings.get(id);
    booking.status = 'cancelled';
    booking.cancelledAt = new Date().toISOString();

    bookings.set(id, booking);

    res.json({ message: 'Booking cancelled', booking });
});

/**
 * GET /api/calendar/user/:userId
 * Get all bookings for a user
 */
router.get('/user/:userId', (req, res) => {
    const { userId } = req.params;

    const userBookings = Array.from(bookings.values()).filter(
        booking => booking.userId === userId && booking.status !== 'cancelled'
    );

    res.json({ bookings: userBookings });
});

export default router;
