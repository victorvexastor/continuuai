import { describe, it, expect, vi } from 'vitest';
import request from 'supertest';
import app from '../src/server.js';

describe('Backend API Tests', () => {
    describe('Health Check', () => {
        it('GET /api/health returns 200', async () => {
            const res = await request(app).get('/api/health');
            expect(res.statusCode).toBe(200);
            expect(res.body).toHaveProperty('status', 'healthy');
            expect(res.body).toHaveProperty('timestamp');
        });
    });

    describe('Authentication Routes', () => {
        it('POST /api/auth/register creates new user', async () => {
            const res = await request(app)
                .post('/api/auth/register')
                .send({
                    email: 'test@neuais.com',
                    password: 'TestPass123!',
                    name: 'Test User'
                });

            expect(res.statusCode).toBe(201);
            expect(res.body).toHaveProperty('token');
            expect(res.body.user).toHaveProperty('email', 'test@neuais.com');
        });

        it('POST /api/auth/register rejects duplicate email', async () => {
            // First registration
            await request(app)
                .post('/api/auth/register')
                .send({
                    email: 'duplicate@neuais.com',
                    password: 'TestPass123!',
                    name: 'First User'
                });

            // Second registration with same email
            const res = await request(app)
                .post('/api/auth/register')
                .send({
                    email: 'duplicate@neuais.com',
                    password: 'TestPass123!',
                    name: 'Second User'
                });

            expect(res.statusCode).toBe(409);
        });

        it('POST /api/auth/login authenticates user', async () => {
            // Register first
            await request(app)
                .post('/api/auth/register')
                .send({
                    email: 'login@neuais.com',
                    password: 'TestPass123!',
                    name: 'Login User'
                });

            // Then login
            const res = await request(app)
                .post('/api/auth/login')
                .send({
                    email: 'login@neuais.com',
                    password: 'TestPass123!'
                });

            expect(res.statusCode).toBe(200);
            expect(res.body).toHaveProperty('token');
        });
    });

    describe('Calendar Routes', () => {
        it('POST /api/calendar/book creates booking', async () => {
            const res = await request(app)
                .post('/api/calendar/book')
                .send({
                    userId: 'test-user-id',
                    startTime: new Date(Date.now() + 86400000).toISOString(),
                    endTime: new Date(Date.now() + 90000000).toISOString(),
                    gpuCount: 1
                });

            expect(res.statusCode).toBe(201);
            expect(res.body.booking).toHaveProperty('id');
        });

        it('POST /api/calendar/book detects conflicts', async () => {
            const startTime = new Date(Date.now() + 86400000).toISOString();
            const endTime = new Date(Date.now() + 90000000).toISOString();

            // First booking
            await request(app)
                .post('/api/calendar/book')
                .send({
                    userId: 'user1',
                    startTime,
                    endTime,
                    gpuCount: 1
                });

            // Conflicting booking
            const res = await request(app)
                .post('/api/calendar/book')
                .send({
                    userId: 'user2',
                    startTime,
                    endTime,
                    gpuCount: 1
                });

            expect(res.statusCode).toBe(409);
        });
    });

    describe('Session Routes', () => {
        it('POST /api/sessions/create creates session', async () => {
            const res = await request(app)
                .post('/api/sessions/create')
                .send({
                    userId: 'test-user',
                    notebookName: 'Test Notebook'
                });

            expect(res.statusCode).toBe(201);
            expect(res.body.session).toHaveProperty('id');
            expect(res.body.session).toHaveProperty('containerId');
        });

        it('GET /api/sessions/:id retrieves session', async () => {
            // Create session first
            const createRes = await request(app)
                .post('/api/sessions/create')
                .send({
                    userId: 'test-user',
                    notebookName: 'Test Notebook'
                });

            const sessionId = createRes.body.session.id;

            // Retrieve it
            const res = await request(app).get(`/api/sessions/${sessionId}`);

            expect(res.statusCode).toBe(200);
            expect(res.body.session).toHaveProperty('id', sessionId);
        });
    });
});
