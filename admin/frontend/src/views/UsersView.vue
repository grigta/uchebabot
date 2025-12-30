<template>
  <v-container>
    <h1 class="text-h4 mb-6">Users</h1>

    <v-card>
      <v-card-title>
        <v-text-field
          v-model="search"
          prepend-icon="mdi-magnify"
          label="Search users"
          single-line
          hide-details
          clearable
          @update:model-value="debouncedSearch"
        />
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="usersStore.users"
        :loading="usersStore.loading"
        :items-per-page="20"
        class="elevation-0"
      >
        <template #item.username="{ item }">
          <span v-if="item.username">@{{ item.username }}</span>
          <span v-else class="text-grey">—</span>
        </template>

        <template #item.name="{ item }">
          {{ item.first_name }} {{ item.last_name || '' }}
        </template>

        <template #item.is_banned="{ item }">
          <v-chip
            :color="item.is_banned ? 'error' : 'success'"
            size="small"
          >
            {{ item.is_banned ? 'Banned' : 'Active' }}
          </v-chip>
        </template>

        <template #item.daily_requests="{ item }">
          {{ item.daily_requests }}/{{ item.custom_daily_limit || 20 }}
        </template>

        <template #item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>

        <template #item.actions="{ item }">
          <v-btn
            v-if="item.is_banned"
            icon="mdi-account-check"
            size="small"
            variant="text"
            color="success"
            @click="unbanUser(item)"
          />
          <v-btn
            v-else
            icon="mdi-account-cancel"
            size="small"
            variant="text"
            color="error"
            @click="banUser(item)"
          />
          <v-btn
            icon="mdi-pencil"
            size="small"
            variant="text"
            @click="editUser(item)"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- Edit Dialog -->
    <v-dialog v-model="editDialog" max-width="400">
      <v-card>
        <v-card-title>Edit User</v-card-title>
        <v-card-text>
          <v-text-field
            v-model.number="editingUser.custom_daily_limit"
            label="Custom Daily Limit"
            type="number"
            hint="Leave empty for default (20)"
            persistent-hint
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="editDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="saveUser">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUsersStore, type User } from '@/stores/users'

const usersStore = useUsersStore()
const search = ref('')
const editDialog = ref(false)
const editingUser = ref<Partial<User>>({})

const headers = [
  { title: 'ID', key: 'id', width: '80px' },
  { title: 'Telegram ID', key: 'telegram_id' },
  { title: 'Username', key: 'username' },
  { title: 'Name', key: 'name' },
  { title: 'Status', key: 'is_banned' },
  { title: 'Requests', key: 'daily_requests' },
  { title: 'Total', key: 'total_requests' },
  { title: 'Created', key: 'created_at' },
  { title: 'Actions', key: 'actions', sortable: false }
]

onMounted(() => {
  usersStore.fetchUsers()
})

let searchTimeout: ReturnType<typeof setTimeout>
function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    usersStore.fetchUsers(1, 20, search.value || undefined)
  }, 300)
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString()
}

async function banUser(user: User) {
  if (confirm(`Ban user @${user.username || user.telegram_id}?`)) {
    await usersStore.banUser(user.id)
  }
}

async function unbanUser(user: User) {
  await usersStore.unbanUser(user.id)
}

function editUser(user: User) {
  editingUser.value = { ...user }
  editDialog.value = true
}

async function saveUser() {
  if (editingUser.value.id) {
    await usersStore.updateUser(editingUser.value.id, {
      custom_daily_limit: editingUser.value.custom_daily_limit || undefined
    })
    editDialog.value = false
  }
}
</script>
