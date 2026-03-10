import jwt from 'jsonwebtoken';
const token = jwt.sign({ id: 'admin', email: 'admin@hiveclip', role: 'admin' }, 'hiveclip-dev-secret', { expiresIn: '1h' });
console.log(token);
