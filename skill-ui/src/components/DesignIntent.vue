<template>
  <v-container fluid>
    <v-row>
    <v-col cols="4">
      <v-row>
        <v-card v-if="this.openapi.info" flat>
          <v-card-title>
            {{ this.openapi.info.title }} v{{ this.openapi.info.version }}
          </v-card-title>
          <v-card-text>
            <sub>{{ this.openapi.info.description }}</sub>
          </v-card-text>
        </v-card>
      </v-row>
      <v-row>
        <v-col>
          <v-card flat>
            <v-card-text>Intents</v-card-text>
          </v-card>
        </v-col>
        <v-col class="text-right">
          <v-tooltip bottom>
            <template v-slot:activator="{ on, attrs }">
              <v-btn icon @click="addIntent"
                     v-bind="attrs"
                     v-on="on"
                     :disabled="!valid"
              > <v-icon
                  large>mdi-message-plus</v-icon>
              </v-btn>
            </template>
            <span>Add Intent</span>
          </v-tooltip>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
        <v-form v-model="valid">
        <v-expansion-panels
            accordion
            focusable
            v-model="intentsPanel"
        > <v-expansion-panel
              v-for="(intent, index) in intents" :key="index">
            <v-expansion-panel-header
                ref="header"
                @keydown.prevent
            > <template v-slot:default="{ open }">
                <span v-if="open" key="0">
                  <v-col class="text-right">
                    <v-text-field
                        autofocus
                        v-model="intent.name"
                        label="Name"
                        :rules="[rules.required, rules.unique(intents.map(e => e.name), index)]"
                        @click.stop
                        @keydown.stop
                        @keydown.space.prevent
                    ></v-text-field>
                    <v-tooltip bottom>
                      <template v-slot:activator="{ on, attrs }">
                        <v-btn icon @click.stop="openDialogDelete(index)"
                               v-bind="attrs"
                               v-on="on"
                        > <v-icon
                            large>mdi-delete-forever</v-icon>
                        </v-btn>
                      </template>
                      <span>Remove Intent</span>
                    </v-tooltip>
                    <v-dialog v-model="dialogDelete" max-width="500px">
                      <v-card>
                        <v-card-title class="headline">Remove this intent?</v-card-title>
                        <v-card-actions>
                          <v-spacer></v-spacer>
                          <v-btn color="blue darken-1" text @click="cancelDelete">Cancel</v-btn>
                          <v-btn color="blue darken-1" text @click="confirmDelete">OK</v-btn>
                          <v-spacer></v-spacer>
                        </v-card-actions>
                      </v-card>
                    </v-dialog>

                  </v-col>
                </span>
                <span v-else key="1">
                  {{ intent.name }}
                </span>
              </template>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-data-table
                  :items="intent.parameters"
                  :headers="headers"
                  item-key="name"
                  hide-default-footer
              >
                <template
                    v-slot:body="{ items }"
                >
                  <tbody>
                  <tr
                      v-for="(param, index) in items"
                      :key="index"
                  >
                    <td>
                      <v-text-field
                          autofocus
                          v-model="param.name"
                          hint="Name"
                          :rules="[rules.required, rules.python, rules.unique(items.map(e => e.name), index)]"
                      ></v-text-field>
                    </td>
                    <td>
                      <v-select
                          :items="types"
                          v-model="param.type"
                          solo
                          style="margin-top: 5px"
                      ></v-select>
                    </td>
                    <td>
                      <v-text-field
                          v-model="param.values"
                          hint="Default"
                          clearable
                      ></v-text-field>
                    </td>
                    <td>
                      <v-tooltip bottom>
                        <template v-slot:activator="{ on, attrs }">
                          <v-btn icon @click.stop="intent.parameters.splice(index, 1)"
                             v-bind="attrs"
                             v-on="on"
                          > <v-icon>mdi-minus-circle</v-icon>
                          </v-btn>
                        </template>
                        <span>Remove attribute</span>
                      </v-tooltip>
                    </td>
                  </tr>
                  <tr>
                    <td colspan="4" align="right">
                      <v-tooltip bottom>
                        <template v-slot:activator="{ on, attrs }">
                          <v-btn icon @click="intent.parameters.push({name: '', type: 'str'})"
                                 v-bind="attrs"
                                 v-on="on"
                          > <v-icon>mdi-plus-circle</v-icon>
                          </v-btn>
                        </template>
                        <span>Add attribute</span>
                      </v-tooltip>
                    </td>
                  </tr>
                  </tbody>
                </template>
              </v-data-table>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-form>
      </v-col>
      </v-row>
    </v-col>
    <v-col>
      <v-row>
        <v-col>
          <v-textarea
              v-model="log"
              readonly
              filled
              outlined
              label="Log"
              id="log"
              rows="17"
          ></v-textarea>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-btn @click="dialogGenerate = true"
              :disabled="!valid || !intents.length"
          >Generate</v-btn>
          <v-dialog v-model="dialogGenerate" max-width="500px">
            <v-card>
              <v-card-title class="headline">Overwrite your skill?</v-card-title>
              <v-card-text>
                <v-list-item>
                  <v-list-item-content>
                    <v-list-item-title>This action overwrites the files:</v-list-item-title>
                    <v-list-item-subtitle>impl/__init__.py</v-list-item-subtitle>
                    <v-list-item-subtitle>impl/test_impl.py</v-list-item-subtitle>
                    <v-list-item-subtitle>app.py</v-list-item-subtitle>
                  </v-list-item-content>
                </v-list-item>
              </v-card-text>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="blue darken-1" text @click="dialogGenerate = false">Cancel</v-btn>
                <v-btn color="blue darken-1" text @click="postIntents">OK</v-btn>
                <v-spacer></v-spacer>
              </v-card-actions>
            </v-card>
          </v-dialog>
          <template>
            <div class="text-center">
              <v-dialog
                  v-model="dialog"
                  width="500"
              >
                <v-card>
                  <v-card-title class="headline red" v-if="error">
                    Error
                  </v-card-title>

                  <v-card-title class="headline" v-else-if="response">
                    Done
                  </v-card-title>

                  <v-card-title class="headline" v-else>
                    Nothing to do
                  </v-card-title>

                  <v-card-text v-if="error">
                    {{error}}: {{error && error.response && error.response.data}}
                  </v-card-text>

                  <v-card-text v-else-if="response">
                    Implementation is saved as {{response}}.
                    <br />
                    <b>You may need to re-start the skill</b>: source re-loading functionality is not there yet.
                  </v-card-text>

                  <v-card-text v-else>
                    Your implementation is identical to already running.
                  </v-card-text>

                  <v-divider></v-divider>

                  <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn
                        color="primary"
                        text
                        @click="dialog = error = response = null;"
                    >
                      Close
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-dialog>
            </div>
          </template>

        </v-col>
      </v-row>
    </v-col>
    </v-row>
  </v-container>
</template>
<script>

export default {

  data: () => ({
      valid: true,
      changed: false,
      openapi: {},
      intents: {},
      types: [],
      request: "{}",
      response: {},
      connection: null,
      log: "",
      intentsPanel: null,
      rules: {
        required: value => !!value || "Name required!",
        python: value => /^[A-Za-z_][A-Za-z0-9_]*$/.test(value) || "Illegal name!",
        unique(list, index) {
          return !list.filter((e, i) => i !== index).includes(list[index]) || "Name must be unique!"
        }
      },
      onClick: false,
      headers: [
        {text: 'Attribute', sortable: false},
        {text: 'Type', sortable: false},
        {text: 'Default', sortable: false},
      ],
      dialog: false,
      error: null,
      dialogDelete: false,
      deletedIndex: -1,
      dialogGenerate: false,
  }),

  watch: {
      valid(v) {
          this.freezeAccordion(!v);
          this.changed = true;
      }
  },

  created: function() {
      this.init();
  },

  methods: {
      init() {
          this.getAPIDescription();
          this.getTypes();
          this.getIntents();
          this.connectLogs();
      },
      freezeAccordion(state = true)  {
          this.$refs.header.filter(e => !e.isActive).forEach(e =>
              state ? e.$el.classList.add("disabled-pointer") : e.$el.classList.remove("disabled-pointer")
          );
          if (state || this.onClick) {
              const activeHeader = this.$refs.header.filter(e => e.isActive)[0];
              [activeHeader.onClick, this.onClick] = [this.onClick, activeHeader.onClick];
          }
      },
      addIntent() {
          this.intents.unshift({name: 'New_Intent', parameters: []});
          this.intentsPanel = 0;
      },
      openDialogDelete(index) {
          this.deletedIndex = index;
          this.dialogDelete = true;
      },
      confirmDelete() {
          this.intents.splice(this.deletedIndex, 1);
          this.deletedIndex = -1;
          this.dialogDelete = false;
      },
      cancelDelete() {
          this.deletedIndex = -1;
          this.dialogDelete = false;
      },
      getIntents() {
          const uri = 'http://localhost:4242/intents'
          this.axios.get(uri).then(
              r => this.intents = r.data
          )
      },
      postIntents() {
          const uri = 'http://localhost:4242/intents'
          this.dialogGenerate = false;
          this.axios.post(uri, this.intents)
              .then(r => this.response = r.status === 204 ? null : r.data)
              .catch(e => this.error = e)
              .finally(() => this.dialog = true)
      },
      getTypes() {
          const uri = 'http://localhost:4242/types'
          this.axios.get(uri).then(
              r => this.types = r.data
          )
      },
      getAPIDescription() {
          const uri = 'http://localhost:4242/openapi.json'
          this.axios.get(uri).then(
              r => this.openapi = r.data
          )
      },
      connectLogs() {

          this.connection = new WebSocket("ws://localhost:4242/logs");

          const self = this
          this.connection.onmessage = function(event) {
            const container = document.getElementById ( "log" )
            container.scrollTop = container.scrollHeight
            self.log += JSON.parse(event.data).msg + "\n"
          }

          this.connection.onopen = function(event) {
            console.log(event)
            console.log("Successfully connected to the logs server...")
          }
      },

  }
};
</script>

<style scoped>
.v-expansion-panel-content .row:first-child {
  margin-top: 12px;
}
.disabled-pointer {
  pointer-events: none;
}
</style>