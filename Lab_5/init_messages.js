db = db.getSiblingDB('messages_db');
db.createCollection('messages');
db.messages.createIndex({recipient: 1});

if (!db.messages.findOne({})) {
    db.messages.insertMany([
        {sender: 'admin', recipient: 'admin', message: 'tralalelo tralala', timestamp: new Date()},
        {sender: 'admin', recipient: 'admin', message: 'lirili larila', timestamp: new Date()},
        {sender: 'admin', recipient: 'admin', message: 'fruli frula', timestamp: new Date()}
    ]);
}