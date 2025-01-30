FROM node:12

ADD package.json /package.json

ENV NODE_PATH=/node_modules
ENV PATH=$PATH:/node_modules/.bin
RUN npm install

COPY . .

CMD ["npm", "run", "dev"]